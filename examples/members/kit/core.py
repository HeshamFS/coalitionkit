# SPDX-License-Identifier: Apache-2.0
"""The protocol side of a member, independent of which framework runs its model.

``MemberCore.handle`` takes one delivered envelope, verifies it against the pinned host key, and
reacts: it joins, accepts the charter through its owner, answers vault queries from a local
policy, lets the brain make offers, consents to a plan through the owner, and lets the brain
commit and report done. Every envelope it sends is signed with the agent key; every consent is
signed with the owner key.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from coalitionkit_contracts import (
    HOST_ONLY_TYPES,
    SchemaValidationError,
    SignatureError,
    new_ulid,
    sign_consent,
    sign_envelope,
    sign_owner_proof,
    validate_envelope,
    verify_envelope,
    verify_projection,
)
from coalitionkit_edges.a2a import EdgeCallError, MemberClient, ReceivedError

from .brain import Brain, offers_instruction, work_instruction
from .identity import MemberIdentity
from .policy import OwnerCallback, VaultPolicy
from .records import MemberLog, Sent, Turn
from .redact import describe

HOST_ONLY: dict[str, Any] = {"audience": "host"}
COALITION: dict[str, Any] = {"audience": "coalition"}


class DeliveryRefused(Exception):
    """A delivery the member will not act on; ``code`` names why."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code


@dataclass(frozen=True)
class Invitation:
    """What a member gets out of band before it joins: the host card, its pinned key, a token."""

    coalition_id: str
    host_card_url: str
    host_key: Ed25519PublicKey
    host_kid: str
    token: str


def _now() -> datetime:
    return datetime.now(UTC)


def _stamp(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


class MemberCore:
    def __init__(
        self,
        identity: MemberIdentity,
        invitation: Invitation,
        brain: Brain | None,
        vault: VaultPolicy,
        owner: OwnerCallback,
    ) -> None:
        self.identity, self.invitation, self.brain = identity, invitation, brain
        self.vault, self.owner = vault, owner
        self.name = identity.name
        self.log = MemberLog()
        self.charter: dict[str, Any] = {}
        self.needs: dict[str, str] = {}
        self.queried: dict[str, str] = {}
        self.plan_tasks: dict[str, list[str]] = {}
        self.consents: dict[str, set[str]] = {}
        self.decided_plan: str | None = None
        self.work_started = False
        self.offers_started = False
        self.joined = False
        self.accepted_revision = 0
        self.approved: set[str] = set()
        self.policy_refusals: list[str] = []
        self._seen: set[str] = set()
        self._lock = asyncio.Lock()
        self._http: httpx.AsyncClient | None = None
        self._client: MemberClient | None = None
        #: The loop the server runs this core on; set at the first delivery.
        self.loop: asyncio.AbstractEventLoop | None = None

    # ---- delivery ---------------------------------------------------------------------------

    async def handle(self, envelope: dict[str, Any]) -> str:
        """Verify and act on one delivered envelope. Raises DeliveryRefused if it is bad."""
        async with self._lock:
            self.loop = asyncio.get_running_loop()
            started = time.perf_counter()
            self.log.received += 1
            kind, sender, body, event_id = self._open(envelope)
            if event_id in self._seen:
                return "duplicate"
            self._seen.add(event_id)
            before = len(self.log.turns)
            summary = await self._dispatch(kind, sender, body)
            if len(self.log.turns) == before:
                self.log.turns.append(Turn(kind, time.perf_counter() - started))
            return summary

    def _open(self, envelope: dict[str, Any]) -> tuple[str, str, dict[str, Any], str]:
        """Validate and authenticate a delivery; return (type, on_behalf_of, payload, event_id)."""
        host = self.invitation
        if envelope.get("coalition_id") != host.coalition_id:
            self.log.received_invalid += 1
            raise DeliveryRefused("wrong_coalition", "not the Coalition this member was invited to")
        try:
            validate_envelope(envelope)
        except SchemaValidationError as exc:
            self.log.received_invalid += 1
            raise DeliveryRefused("schema_invalid", str(exc)[:200]) from exc
        try:
            if envelope["type"] == "coalition.projection":
                verify_projection(envelope, host.host_key, expected_kid=host.host_kid)
                source = envelope["payload"]["source"]
                return (
                    source["type"],
                    source["on_behalf_of"],
                    envelope["payload"]["payload"],
                    source["event_id"],
                )
            host_only = envelope["type"] in HOST_ONLY_TYPES | {"coalition.error"}
            from_host = envelope["sender"] == host.host_card_url
            if host_only or from_host:
                # Anything the host originates (and every receipt or error) must carry the host
                # key's signature; nobody else may send these types.
                if not from_host or envelope["on_behalf_of"] != "host":
                    raise DeliveryRefused("not_authorized", "host-only type from another sender")
                verify_envelope(envelope, host.host_key, expected_kid=host.host_kid)
            else:
                # An original from another member: its card is not ours to pin, so only the
                # schema, the Coalition and the host-authenticated channel vouch for it.
                self.log.unverified_peer_originals += 1
        except SignatureError as exc:
            raise DeliveryRefused("bad_signature", str(exc)[:200]) from exc
        return (
            envelope["type"],
            envelope["on_behalf_of"],
            envelope["payload"],
            envelope["event_id"],
        )

    async def _dispatch(self, kind: str, sender: str, body: dict[str, Any]) -> str:
        if kind == "coalition.charter":
            return await self._on_charter(body)
        if kind == "coalition.need":
            self.needs[body["need_id"]] = body["description"].split(":")[0].strip()
            return "need noted"
        if kind == "coalition.query":
            return await self._on_query(body)
        if kind == "coalition.propose":
            return await self._on_propose(body)
        if kind == "coalition.decide":
            subject = body["subject"]
            if sender != self.name and subject["kind"] == "plan" and body["consent"]:
                self.consents.setdefault(subject["id"], set()).add(sender)
                await self._maybe_work()
            return "decision noted"
        if kind == "coalition.dissolve":
            self.log.dissolved = body["reason"]
            return "dissolved"
        return "ignored"

    # ---- reactions --------------------------------------------------------------------------

    async def _on_charter(self, charter: dict[str, Any]) -> str:
        self.charter = charter
        if not self.joined:
            outcome = await self._send("join", self._join_body(), HOST_ONLY)
            if outcome != "accepted":
                return f"join {outcome}"
            self.joined = True
        newer = charter["revision"] > self.accepted_revision
        if newer and await self.owner.accept_charter(charter):
            revision = charter["revision"]
            outcome = await self._decide("charter", self.invitation.coalition_id, revision, True)
            if outcome == "accepted":
                self.accepted_revision = revision
        return "charter handled"

    def _join_body(self) -> dict[str, Any]:
        jwk = self.identity.owner_jwk()
        proof = sign_owner_proof(
            self.invitation.coalition_id,
            self.name,
            self.identity.card_url,
            jwk,
            self.identity.owner_key,
        )
        return {
            "card_url": self.identity.card_url,
            "owner_key": jwk,
            "owner_proof": proof,
            "roles_requested": ["member"],
            "surfaces": [],
            "vault": "local",
        }

    async def _on_query(self, query: dict[str, Any]) -> str:
        result = self.vault.answer(query["kind"], query["subject"])
        await self._send("answer", {"query_id": query["query_id"], "result": result}, HOST_ONLY)
        if query["kind"] == "feasible" and "task_id" in query:
            self.queried[query["task_id"]] = result
        if not self.offers_started and self.needs and set(self.needs) <= set(self.queried):
            self.offers_started = True
            await self._offers_turn()
        return "query answered"

    async def _offers_turn(self) -> None:
        tasks: list[dict[str, Any]] = []
        for need_id, label in sorted(self.needs.items(), key=lambda kv: kv[1]):
            if self.queried.get(need_id) == "yes" and label in self.vault.terms:
                terms = self.vault.terms[label]
                tasks.append(
                    {
                        "need_id": need_id,
                        "label": label,
                        "minutes": terms.minutes,
                        "money": terms.money,
                        "effort": terms.effort,
                    }
                )
        if tasks:
            await self._turn("offers", offers_instruction(self.name, tasks))

    async def _on_propose(self, body: dict[str, Any]) -> str:
        for plan in body["plans"]:
            mine = [a["task_id"] for a in plan["assignments"] if a["assignee"] == self.name]
            self.plan_tasks[plan["plan_id"]] = mine
            agreed = await self.owner.consent_plan(plan["plan_id"], mine)
            outcome = await self._decide("plan", plan["plan_id"], plan["revision"], agreed)
            if agreed and outcome == "accepted":
                self.decided_plan = plan["plan_id"]
                self.consents.setdefault(plan["plan_id"], set()).add(self.name)
                break
        await self._maybe_work()
        return "plan handled"

    async def _maybe_work(self) -> None:
        plan = self.decided_plan
        if plan is None or self.work_started:
            return
        if not set(self.charter["deciders"]) <= self.consents.get(plan, set()):
            return
        self.work_started = True
        tasks = [
            {"task_id": task_id, "label": self.needs.get(task_id, task_id)}
            for task_id in self.plan_tasks.get(plan, [])
        ]
        if tasks:
            await self._turn("work", work_instruction(self.name, tasks))

    async def _turn(self, kind: str, instruction: str) -> None:
        if self.brain is None:
            return
        self.log.prompts.append(instruction)
        started = time.perf_counter()
        before = len(self.log.uses)
        try:
            await self.brain.run(instruction, _Tools(self), self.log.uses.append)
        except Exception as exc:
            self.log.turn_errors.append(f"{kind}: {describe(exc)}")
        calls = len(self.log.uses) - before
        elapsed = time.perf_counter() - started
        self.log.turns.append(Turn(kind, elapsed, elapsed, calls))

    # ---- sending ----------------------------------------------------------------------------

    async def _ensure_client(self) -> MemberClient:
        if self._client is None:
            host = self.invitation
            self._http = httpx.AsyncClient(timeout=httpx.Timeout(120.0))
            self._client = await MemberClient.connect(
                self._http, host.host_card_url, host.token, host.host_key, host.host_kid
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
        if self._http is not None:
            await self._http.aclose()

    def policy_refusal(self, reason: str) -> str:
        """Record an action the owner's policy stopped before anything was signed or sent."""
        self.policy_refusals.append(reason)
        return f"refused: {reason}"

    async def send(self, kind: str, body: dict[str, Any], scope: dict[str, Any]) -> str:
        """Sign and send one envelope; return ``accepted`` or the refusal code."""
        return await self._send(kind, body, scope)

    async def _send(self, kind: str, body: dict[str, Any], scope: dict[str, Any]) -> str:
        envelope: dict[str, Any] = {
            "ext_version": "0.1",
            "coalition_id": self.invitation.coalition_id,
            "event_id": new_ulid(),
            "type": f"coalition.{kind}",
            "sender": self.identity.card_url,
            "on_behalf_of": self.name,
            "scope": scope,
            "payload": body,
        }
        envelope["sig"] = sign_envelope(envelope, self.identity.agent_key, self.identity.agent_kid)
        errors: tuple[str, ...] = ()
        try:
            validate_envelope(envelope)
        except SchemaValidationError as exc:
            errors = tuple(exc.errors)
        started = time.perf_counter()
        outcome = "accepted"
        try:
            client = await self._ensure_client()
            await client.send(envelope, validate=False)
        except ReceivedError as exc:
            outcome = exc.code
        except EdgeCallError as exc:
            outcome = f"transport:{type(exc).__name__}"
        elapsed = time.perf_counter() - started
        self.log.sent.append(
            Sent(envelope["type"], envelope["event_id"], not errors, errors, outcome, elapsed)
        )
        return outcome

    async def decide(self, kind: str, subject_id: str, revision: int, consent: bool) -> str:
        return await self._decide(kind, subject_id, revision, consent)

    async def _decide(self, kind: str, subject_id: str, revision: int, consent: bool) -> str:
        body: dict[str, Any] = {
            "subject": {"kind": kind, "id": subject_id, "revision": revision},
            "choice": subject_id,
            "consent": consent,
            "decided_at": _stamp(_now()),
        }
        body["consent_sig"] = sign_consent(
            self.invitation.coalition_id,
            body,
            self.identity.owner_key,
            self.identity.owner_kid,
            participant=self.name,
        )
        scope = COALITION if kind == "plan" else HOST_ONLY
        return await self._send("decide", body, scope)


class _Tools:
    """The toolbox the brain sees: protocol actions as plain async calls returning text."""

    def __init__(self, core: MemberCore) -> None:
        self._core = core

    async def make_offer(self, need_id: str, minutes: int, money: int, effort: str) -> str:
        core = self._core
        label = core.needs.get(need_id)
        if label is None:
            return "refused: unknown need_id"
        # The owner's policy, not the model, decides what may be offered.
        allowed = await core.owner.offer_terms(label)
        if core.queried.get(need_id) != "yes" or allowed is None:
            return core.policy_refusal(f"offer for {label} is not allowed by the owner")
        if (minutes, money, effort) != (allowed.minutes, allowed.money, allowed.effort):
            return core.policy_refusal(
                f"terms for {label} are fixed by the owner: minutes {allowed.minutes}, "
                f"money {allowed.money}, effort {allowed.effort}"
            )
        body: dict[str, Any] = {
            "offer_id": f"{core.name}-{label}",
            "target": {"kind": "need", "id": need_id},
            "capacity": 1,
            "cost": {"minutes": minutes, "money": money, "effort": effort},
            "valid_until": _stamp(_now() + timedelta(hours=1)),
        }
        outcome = await core.send("offer", body, HOST_ONLY)
        if outcome == "accepted":
            return f"accepted: offer for {label} recorded"
        return f"refused: {outcome}"

    async def commit_to_task(self, task_id: str) -> str:
        core = self._core
        if task_id not in core.plan_tasks.get(core.decided_plan or "", []):
            return core.policy_refusal("that task is not assigned to you by the decided plan")
        commitment = new_ulid()
        body = {"commitment_id": commitment, "task_id": task_id, "status": "pending"}
        outcome = await core.send("commit", body, HOST_ONLY)
        if outcome != "accepted":
            return f"refused: {outcome}"
        if not await core.owner.approve_commitment(task_id):
            return "refused: the owner declined to approve the commitment"
        approval = await core.decide("commitment", commitment, 1, True)
        if approval != "accepted":
            return f"refused: {approval}"
        core.approved.add(task_id)
        return f"approved: the owner approved the commitment for {core.needs.get(task_id, task_id)}"

    async def report_done(self, task_id: str, evidence_ref: str) -> str:
        core = self._core
        if task_id not in core.approved:
            return core.policy_refusal("that task has no commitment approved by your owner")
        body = {
            "task_id": task_id,
            "evidence": [{"kind": "result", "ref": evidence_ref, "verified_by": core.name}],
        }
        outcome = await core.send("done", body, HOST_ONLY)
        return "accepted: task reported done" if outcome == "accepted" else f"refused: {outcome}"
