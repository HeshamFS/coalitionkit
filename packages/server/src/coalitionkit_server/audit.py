# SPDX-License-Identifier: Apache-2.0
"""A dedicated async loop bridges the runtime's synchronous audit hook."""

import asyncio
import time
from collections.abc import Callable
from threading import Thread

from coalitionkit_contracts import Envelope
from coalitionkit_models import (
    CostMeter,
    CostRecord,
    ModelGateway,
    UnpricedModelError,
    load_price_table,
)
from coalitionkit_models.settings import Settings as ModelSettings
from coalitionkit_runtime.steward import ReviewContext, Verdict
from coalitionkit_steward import Steward, StewardContext
from coalitionkit_steward.conditions import Subject, evaluate_all
from coalitionkit_steward.policy import core_policies

from .adapter import Document


class AuditLoop:
    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        self.thread = Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()

    def close(self) -> None:
        asyncio.run_coroutine_threadsafe(self.loop.shutdown_default_executor(), self.loop).result()
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join()
        self.loop.close()


MembersOf = Callable[[str], frozenset[str] | None]


class StewardAdapter:
    """Bridges the runtime's synchronous hook to the Steward.

    ``members`` names a Coalition's members. Without it the Steward cannot tell who receives
    a proposal set and fails closed (escalates, sends nothing to a model).
    """

    def __init__(
        self,
        steward: Steward | Callable[[], Steward],
        runner: AuditLoop,
        members: MembersOf | None = None,
    ) -> None:
        self.runner = runner
        # (event type, seconds, action) for each review: how long the Steward takes, per event.
        self.timings: list[tuple[str, float, str]] = []
        # Told when a plan set enters and leaves review: (phase, coalition, seconds, action).
        self.on_plan_review: Callable[[str, str, float, str], None] | None = None
        # Told after every review, inside the host's transaction: a dict with ``coalition``,
        # ``event_id``, ``type``, ``by``, ``seconds``, ``action`` and ``policy_id``.
        self.on_review: Callable[[dict[str, object]], None] | None = None
        self._members = members
        self._policies = core_policies()
        self._ready = None
        self.steward = steward if isinstance(steward, Steward) else None
        if not isinstance(steward, Steward):
            self._ready = asyncio.run_coroutine_threadsafe(asyncio.to_thread(steward), runner.loop)

    def review(self, envelope: Document, *, context: ReviewContext | None = None) -> Verdict:
        started = time.monotonic()
        watching = envelope.get("type") == "coalition.propose" and self.on_plan_review is not None
        coalition = str(envelope.get("coalition_id", ""))
        if watching and self.on_plan_review is not None:
            self.on_plan_review("start", coalition, 0.0, "")
        verdict = self._review(envelope, context)
        if watching and self.on_plan_review is not None:
            self.on_plan_review("end", coalition, time.monotonic() - started, verdict.action)
        self.timings.append((str(envelope.get("type")), time.monotonic() - started, verdict.action))
        if self.on_review is not None:
            self.on_review(
                {
                    "coalition": coalition,
                    "event_id": envelope.get("event_id"),
                    "type": envelope.get("type"),
                    "by": envelope.get("on_behalf_of"),
                    "seconds": time.monotonic() - started,
                    "action": verdict.action,
                    "policy_id": verdict.policy_id,
                }
            )
        del self.timings[:-2000]
        return verdict

    def _review(self, envelope: Document, context: ReviewContext | None) -> Verdict:
        members = self._members(str(envelope.get("coalition_id", ""))) if self._members else None
        facts = StewardContext(
            members=context.recipients if context else members,
            consented=context.consented if context else (members or frozenset()),
            participant_count=len(context.members) if context else len(members or ()),
        )
        parsed = Envelope.model_validate(envelope)
        if self.steward is None:
            assert self._ready is not None
            if self._ready.done():
                try:
                    self.steward = self._ready.result()
                except Exception:
                    return Verdict("block", "steward-selftest-failed")
            else:
                matches = evaluate_all(self._policies, Subject.from_envelope(parsed), facts)
                if parsed.type == "coalition.propose" or matches:
                    return Verdict("block", "steward-selftest-pending")
                return Verdict()
        future = asyncio.run_coroutine_threadsafe(
            self.steward.review(parsed, context=facts),
            self.runner.loop,
        )
        body = future.result().body
        return Verdict(body.action, body.policy_id, tuple(body.redact))


class RoomMeter(CostMeter):
    """The real price table, but a model missing from it costs nothing instead of failing the
    call after the provider has already answered."""

    def record(self, coalition_id: str, participant: str, model: str, **usage: int) -> CostRecord:
        try:
            return super().record(coalition_id, participant, model, **usage)
        except UnpricedModelError:
            return self._add(
                CostRecord(
                    coalition_id,
                    participant,
                    model,
                    usage.get("prompt_tokens", 0),
                    usage.get("completion_tokens", 0),
                    usage.get("cached_tokens", 0),
                    0,
                    reasoning_tokens=usage.get("reasoning_tokens", 0),
                )
            )


def gateway() -> ModelGateway:
    return ModelGateway(ModelSettings(), meter=RoomMeter(load_price_table()))
