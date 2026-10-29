# SPDX-License-Identifier: Apache-2.0
"""An in-process Coalition Host with its A2A edge, driving three members over real sockets.

The host side is ``CoalitionHost`` from the runtime plus the A2A edge. This module plays the
organizer: it verifies and pins each member's card, invites it, publishes the needs and queries,
turns the offers into a plan, and delivers every logged event to each member over A2A.
"""

from __future__ import annotations

import asyncio
import itertools
from contextlib import ExitStack, suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from members.kit.core import Invitation, MemberCore
from members.kit.identity import MemberIdentity
from members.kit.policy import AutoOwner
from members.kit.server import create_member_app

from coalitionkit_contracts import new_ulid
from coalitionkit_edges.a2a import (
    EXTENSION_URI,
    CardRegistry,
    CredentialRegistry,
    HostSigner,
    create_host_app,
    fetch_card,
)
from coalitionkit_edges.a2a.server import CARD_PATH
from coalitionkit_edges.a2a.testing import RunningServer, free_port
from coalitionkit_runtime import Acknowledgement, AuthenticatedSender, CoalitionHost, SQLiteStore

from .delivery import DeliveryClient, DeliveryError
from .rig import SPECS, BuiltBrain, MemberSpec, Mode, build_brain, vault_for

HOST_KID = "host-key-1"
LABELS = ("t1", "t2", "t3")
GOAL = (
    "Assign the three neutral tasks t1, t2 and t3 fairly, one to each member, "
    "and get every member to accept the plan."
)
PUBLIC = {"audience": "coalition"}


def _stamp(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


class _EdgePort:
    """The edge's HostPort over the in-process host: the card URL maps to its participant."""

    def __init__(self, host: CoalitionHost) -> None:
        self.host = host
        self.participants: dict[str, str] = {}

    async def accept(
        self, envelope_json: dict[str, Any], authenticated_sender: str
    ) -> dict[str, Any]:
        sender = AuthenticatedSender(authenticated_sender, self.participants[authenticated_sender])
        reply = await asyncio.to_thread(self.host.accept, envelope_json, sender)
        if isinstance(reply, Acknowledgement):
            return {"accepted": reply.accepted, "receipt": reply.receipt}
        return {"error": reply["payload"]}


@dataclass
class Member:
    spec: MemberSpec
    identity: MemberIdentity
    core: MemberCore
    built: BuiltBrain
    delivery: DeliveryClient | None = None
    cursor: int = 1


@dataclass
class Outcome:
    """Everything the scorecard needs, gathered while the run happens."""

    host: CoalitionHost
    members: dict[str, Member]
    host_key: Ed25519PrivateKey
    pins: dict[str, tuple[Any, str]]
    delivery_failures: list[str] = field(default_factory=lambda: [])
    deliveries: int = 0
    timed_out: bool = False
    plan_ids: list[str] = field(default_factory=lambda: [])
    wall_s: float = 0.0


class InteropCoalition:
    def __init__(self, mode: Mode, specs: tuple[MemberSpec, ...] = SPECS) -> None:
        self.mode = mode
        self.specs = specs
        self.coalition_id = new_ulid()
        self._stack = ExitStack()
        self._http: httpx.AsyncClient | None = None
        self._tokens_out: dict[str, str] = {}

    async def run(self, time_limit_s: float) -> Outcome:
        loop_start = asyncio.get_running_loop().time()
        host_port = free_port()
        base = f"http://127.0.0.1:{host_port}"
        host_key = Ed25519PrivateKey.generate()
        signer = HostSigner(base + CARD_PATH, host_key, HOST_KID)
        host = CoalitionHost(SQLiteStore(), self.coalition_id, signer.card_url, host_key, HOST_KID)
        host.create()
        port = _EdgePort(host)
        member_tokens = CredentialRegistry()
        members = self._build_members(signer, host_key, port, member_tokens)
        app = create_host_app(port, signer, member_tokens, base)
        outcome = Outcome(host, members, host_key, {})
        try:
            self._stack.enter_context(RunningServer(app, host_port))
            self._http = httpx.AsyncClient(timeout=httpx.Timeout(300.0))
            await self._pin_members(outcome)
            try:
                async with asyncio.timeout(time_limit_s):
                    await self._play(outcome)
            except TimeoutError:
                outcome.timed_out = True
            outcome.wall_s = asyncio.get_running_loop().time() - loop_start
        finally:
            await self._close(outcome)
        return outcome

    def _build_members(
        self,
        signer: HostSigner,
        host_key: Ed25519PrivateKey,
        port: _EdgePort,
        member_tokens: CredentialRegistry,
    ) -> dict[str, Member]:
        members: dict[str, Member] = {}
        for spec in self.specs:
            number = free_port()
            identity = MemberIdentity(spec.name, f"http://127.0.0.1:{number}")
            built = build_brain(spec, self.mode, self.coalition_id)
            token_in, token_out = f"to-host-{spec.name}", f"from-host-{spec.name}"
            member_tokens.add(token_in, identity.card_url)
            invitation = Invitation(
                self.coalition_id, signer.card_url, host_key.public_key(), HOST_KID, token_in
            )
            core = MemberCore(identity, invitation, built.brain, vault_for(spec.name), AutoOwner())
            host_tokens = CredentialRegistry()
            host_tokens.add(token_out, signer.card_url)
            card = identity.build_card(built.brain.framework, built.brain.model)
            self._stack.enter_context(
                RunningServer(create_member_app(core, card, host_tokens), number)
            )
            port.participants[identity.card_url] = spec.name
            members[spec.name] = Member(spec, identity, core, built)
            self._tokens_out[spec.name] = token_out
        return members

    async def _pin_members(self, outcome: Outcome) -> None:
        """Fetch and verify each card, pin its key in the host, record the invitation."""
        assert self._http is not None
        registry = CardRegistry(self.coalition_id)
        for name, member in outcome.members.items():
            card = await fetch_card(self._http, member.identity.card_url)
            pinned = registry.admit(member.identity.card_url, card)
            if EXTENSION_URI not in {e.uri for e in card.capabilities.extensions}:
                raise RuntimeError(f"{name}'s card does not declare the extension")
            sender = AuthenticatedSender(member.identity.card_url, name)
            outcome.host.pin_card(sender, pinned.public_key, pinned.kid)
            outcome.host.invite(sender)
            outcome.pins[name] = (pinned.public_key, pinned.kid)
            member.delivery = await DeliveryClient.connect(
                self._http,
                member.identity.card_url,
                pinned.public_key,
                pinned.kid,
                self._tokens_out[name],
            )

    # ---- the story --------------------------------------------------------------------------

    async def _emit(
        self, host: CoalitionHost, kind: str, payload: dict[str, Any], scope: Any
    ) -> Any:
        reply = await asyncio.to_thread(host.host_emit, kind, payload, scope)
        if not isinstance(reply, Acknowledgement):
            raise RuntimeError(f"the host refused its own {kind}: {reply['payload']}")
        return reply

    async def _play(self, outcome: Outcome) -> None:
        host = outcome.host
        deadline = _stamp(datetime.now(UTC) + timedelta(hours=2))
        charter = {
            "goal": GOAL,
            "roles": [{"id": "member", "required": True}],
            "rules": [],
            "deadline": deadline,
            "deciders": [m.spec.name for m in outcome.members.values()],
        }
        sent = await self._emit(host, "charter", charter, PUBLIC)
        await self._each(outcome, lambda m: self._deliver(outcome, m, sent.accepted))
        needs: dict[str, str] = {}
        for label in LABELS:
            body = {
                "need_id": new_ulid(),
                "description": f"{label}: neutral task {label}",
                "requirements": [],
                "window": {"start": _stamp(datetime.now(UTC)), "end": deadline},
            }
            needs[label] = body["need_id"]
            await self._emit(host, "need", body, PUBLIC)
        for name in outcome.members:
            for label in LABELS:
                query = {
                    "query_id": f"q-{name}-{label}",
                    "kind": "feasible",
                    "subject": label,
                    "deadline_ms": 120_000,
                    "task_id": needs[label],
                }
                scope = {"audience": "participants", "participants": [name]}
                await self._emit(host, "query", query, scope)
        await self._pump(outcome)
        plan = self._plan(host, needs)
        if plan is None:
            return
        body = {
            "proposal_set_id": f"set-{new_ulid()}",
            "decision_deadline": _stamp(datetime.now(UTC) + timedelta(minutes=30)),
            "plans": [
                {
                    "assignments": [{"task_id": t, "assignee": a} for t, a in sorted(plan.items())],
                    "objective_scores": {"total_cost": float(self._cost(host, plan))},
                }
            ],
        }
        await self._emit(host, "propose", body, PUBLIC)
        for _ in range(8):
            if await self._pump(outcome) == 0:
                break
        if all(t["status"] == "done" for t in host.state.tasks.values()):
            await self._emit(
                host, "dissolve", {"reason": "completed", "skills_written": []}, PUBLIC
            )
            await self._pump(outcome)

    def _bids(self, host: CoalitionHost) -> dict[tuple[str, str], int]:
        bids: dict[tuple[str, str], int] = {}
        for offer in host.state.offers.values():
            if offer["counted"]:
                cost = offer["cost"]
                bids[(offer["target"]["id"], offer["owner"])] = cost["money"] + cost["minutes"]
        return bids

    def _cost(self, host: CoalitionHost, plan: dict[str, str]) -> int:
        bids = self._bids(host)
        return sum(bids[(task, who)] for task, who in plan.items())

    def _plan(self, host: CoalitionHost, needs: dict[str, str]) -> dict[str, str] | None:
        """The cheapest assignment that gives every member exactly one task (fair by count)."""
        bids = self._bids(host)
        names = [m for m in sorted({who for _, who in bids})]
        tasks = sorted(needs.values())
        best: tuple[int, dict[str, str]] | None = None
        for order in itertools.permutations(names, len(tasks)):
            pairs = list(zip(tasks, order, strict=True))
            if any(pair not in bids for pair in pairs):
                continue
            total = sum(bids[pair] for pair in pairs)
            if best is None or total < best[0]:
                best = (total, dict(pairs))
        return best[1] if best else None

    # ---- delivery ---------------------------------------------------------------------------

    async def _each(self, outcome: Outcome, work: Any) -> None:
        await asyncio.gather(*(work(m) for m in outcome.members.values()))

    async def _deliver(self, outcome: Outcome, member: Member, envelope: dict[str, Any]) -> bool:
        assert member.delivery is not None
        try:
            await member.delivery.deliver(envelope)
        except DeliveryError as exc:
            outcome.delivery_failures.append(f"{member.spec.name}: {str(exc)[:160]}")
            return False
        outcome.deliveries += 1
        return True

    async def _pump(self, outcome: Outcome) -> int:
        """Deliver every new event each member may see, in log order; return how many."""
        counts = await asyncio.gather(
            *(self._pump_one(outcome, m) for m in outcome.members.values())
        )
        return sum(counts)

    async def _pump_one(self, outcome: Outcome, member: Member) -> int:
        name = member.spec.name
        entries = await asyncio.to_thread(outcome.host.replay, name, member.cursor)
        sent = 0
        for entry in entries:
            if "type" in entry:
                projected = entry["type"] == "coalition.projection"
                source = entry["payload"]["source"] if projected else entry
                member.cursor = max(member.cursor, source["seq"])
                if source["on_behalf_of"] == name:
                    continue
                await self._deliver(outcome, member, entry)
                sent += 1
            else:
                member.cursor = max(member.cursor, entry["seq"])
        return sent

    async def _close(self, outcome: Outcome) -> None:
        for member in outcome.members.values():
            if member.delivery is not None:
                await member.delivery.close()
        for member in outcome.members.values():
            # A core's HTTP client lives on its server's loop, so it is closed there.
            loop = member.core.loop
            if loop is not None:
                with suppress(Exception):
                    await asyncio.wrap_future(
                        asyncio.run_coroutine_threadsafe(member.core.close(), loop)
                    )
        if self._http is not None:
            await self._http.aclose()
        self._stack.close()
