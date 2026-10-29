# SPDX-License-Identifier: Apache-2.0
"""A dedicated async loop bridges the runtime's synchronous audit hook."""

import asyncio
from collections.abc import Callable
from threading import Thread

from coalitionkit_contracts import Envelope
from coalitionkit_models import ModelGateway
from coalitionkit_models.settings import Settings as ModelSettings
from coalitionkit_runtime.steward import Verdict
from coalitionkit_steward import Steward, StewardContext

from .adapter import Document


class AuditLoop:
    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        self.thread = Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()

    def close(self) -> None:
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
        self, steward: Steward, runner: AuditLoop, members: MembersOf | None = None
    ) -> None:
        self.steward, self.runner = steward, runner
        self._members = members

    def review(self, envelope: Document) -> Verdict:
        members = self._members(str(envelope.get("coalition_id", ""))) if self._members else None
        future = asyncio.run_coroutine_threadsafe(
            self.steward.review(
                Envelope.model_validate(envelope), context=StewardContext(members=members)
            ),
            self.runner.loop,
        )
        body = future.result().body
        return Verdict(body.action, body.policy_id, tuple(body.redact))


def gateway() -> ModelGateway:
    return ModelGateway(ModelSettings())
