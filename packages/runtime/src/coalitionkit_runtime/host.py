# SPDX-License-Identifier: Apache-2.0
"""The single writer: validate, commit an event and receipt, then wake readers."""

from __future__ import annotations

import json
from collections.abc import Callable
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from coalitionkit_contracts import (
    HOST_FIELDS,
    DecisionExpiredError,
    OwnerKeyConflictError,
    SchemaValidationError,
    SignatureError,
    StaleSubjectError,
    StoredSubmission,
    check_decision_window,
    check_owner_key_unique,
    check_revision,
    classify_submission,
    genesis_hash,
    is_ulid,
    jwk_thumbprint,
    jwk_to_public_key,
    new_ulid,
    next_revision,
    prev_hash,
    receipt_payload,
    sign_envelope,
    submission_digest,
    validate_envelope,
    verify_consent,
    verify_envelope,
    verify_owner_proof,
)

from .bus import Bus
from .cache import HostCache
from .consents import ConsentLedger
from .identity import IdentityRegistry
from .lifecycle import State
from .projector import delivery, derive_scope, projection
from .rules import Refusal, authorize, require, scope_check, stage_check
from .steward import FakeSteward, Steward, Verdict
from .store import Document, EventStore, Transaction


@dataclass(frozen=True)
class AuthenticatedSender:
    card_url: str
    participant: str


@dataclass(frozen=True)
class Acknowledgement[T = Document | None]:
    accepted: T
    receipt: Document


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class CoalitionHost:
    def __init__(
        self,
        store: EventStore,
        coalition_id: str,
        card_url: str,
        private_key: Ed25519PrivateKey,
        kid: str,
        *,
        steward: Steward | None = None,
        clock: Callable[[], str] = utc_now,
        bus: Bus | None = None,
    ) -> None:
        self.store, self.coalition_id, self.card_url = store, coalition_id, card_url
        self.private_key, self.kid, self.clock = private_key, kid, clock
        self.steward = steward or FakeSteward()
        self.bus = bus or Bus()
        self._identities = IdentityRegistry(store, coalition_id)
        self.cards = self._identities.cards
        self.invitations = self._identities.invitations
        self._cache = HostCache(store, coalition_id)
        self.policy: Callable[[Document], str | None] = lambda _: None
        self.rate_limit: Callable[[AuthenticatedSender], int | None] = lambda _: None

    def create(self) -> None:
        self.store.create(self.coalition_id, self.card_url, self.clock())

    def pin_card(self, sender: AuthenticatedSender, key: Ed25519PublicKey, kid: str) -> None:
        """Adapter supplies a card key after verifying its signature, expiry and revocation."""
        self._identities.pin(sender.card_url, sender.participant, key, kid)

    def invite(self, sender: AuthenticatedSender) -> None:
        """Record the organizer's invitation binding a participant to its authenticated card."""
        self._identities.invite(sender.participant, sender.card_url)

    @property
    def state(self) -> State:
        with self._cache.transaction() as tx:
            return deepcopy(self._cache.refresh(tx, self.clock()))

    def open_consents(self, viewer: str) -> list[Document]:
        """Return current pending subjects for this decider, after clock expiry."""
        with self._cache.transaction() as tx:
            self._cache.refresh(tx, self.clock())
            return ConsentLedger(tx, self.coalition_id).pending_for(viewer)

    def state_document(self) -> Document:
        """Host-only JSON state; viewer surfaces use view() instead."""
        return asdict(self.state)

    def sign(self, kind: str, payload: Document, scope: Document) -> Document:
        envelope: Document = {
            "ext_version": "0.1",
            "coalition_id": self.coalition_id,
            "event_id": new_ulid(),
            "type": f"coalition.{kind}",
            "sender": self.card_url,
            "on_behalf_of": "host",
            "scope": deepcopy(scope),
            "payload": deepcopy(payload),
        }
        envelope["sig"] = sign_envelope(envelope, self.private_key, self.kid)
        return envelope

    def accept(
        self,
        envelope: Document,
        authenticated_sender: AuthenticatedSender,
        *,
        extension_activated: bool = True,
    ) -> Acknowledgement | Document:
        return self._accept(deepcopy(envelope), authenticated_sender, False, extension_activated)

    def _accept(
        self,
        event: Document,
        sender: AuthenticatedSender,
        host: bool,
        activated: bool,
        sources: list[str] | None = None,
    ) -> Acknowledgement | Document:
        try:
            require(activated, "extension_not_activated")
            require(
                event.get("sender") == sender.card_url
                and event.get("on_behalf_of") == sender.participant,
                "sender_mismatch",
            )
            with self._cache.transaction() as tx:
                result = self._transaction(tx, event, sender, host, sources or [])
        except Refusal as exc:
            return self._error(event, sender, exc.code, exc.detail)
        except DecisionExpiredError:
            return self._error(event, sender, "deadline_exceeded", {})
        except StaleSubjectError:
            return self._error(event, sender, "stale_subject", {})
        self.bus.publish(self.coalition_id, result.receipt["payload"]["seq"])
        return result

    def _transaction(
        self,
        tx: Transaction,
        event: Document,
        sender: AuthenticatedSender,
        host: bool,
        source_ids: list[str],
    ) -> Acknowledgement:
        now = self.clock()
        row = tx.execute(
            "SELECT sender, digest, body FROM events WHERE coalition_id = ? AND event_id = ?",
            (
                str(event.get("coalition_id", "")),
                event["event_id"] if is_ulid(event.get("event_id")) else "",
            ),
        ).fetchone()
        try:
            outcome = classify_submission(
                StoredSubmission(row[0], row[1]) if row else None, sender.card_url, event
            )
        except ValueError, TypeError:
            outcome = "mismatch" if row else "new"
        require(outcome != "mismatch", "duplicate_mismatch")
        if outcome == "replay":
            receipt = tx.execute(
                "SELECT body FROM receipts WHERE coalition_id = ? AND event_id = ?",
                (self.coalition_id, event["event_id"]),
            ).fetchone()
            state = self._cache.refresh(tx, now)
            return self._ack(state, json.loads(row[2]), json.loads(receipt[0]), sender.participant)
        retry = self.rate_limit(sender)
        if retry is not None:
            raise Refusal("rate_limited", {"retry_after_ms": retry})
        try:
            validate_envelope(event)
            require(event["coalition_id"] == self.coalition_id, "schema_invalid")
        except SchemaValidationError, ValueError, TypeError:
            raise Refusal("schema_invalid") from None
        state = self._cache.refresh(tx, now)
        self._identity(state, event, sender, host)
        stage_check(state, event, host)
        authorize(state, event, host, now)
        sources = self._sources(state, event, source_ids)
        scope_check(state, event, sources)
        ledger = ConsentLedger(tx, self.coalition_id)
        if event["type"] == "coalition.decide":
            body = event["payload"]
            subject = state.subject(body["subject"]["kind"], body["subject"]["id"])
            if "decision_deadline" in subject:
                check_decision_window(subject["decision_deadline"], now)
            check_revision(body["subject"]["revision"], subject["revision"])
            require(subject.get("status") != "superseded", "stale_subject")
            require(
                ledger.answer(
                    body["subject"], subject["revision"], sender.participant, body["consent"]
                )
            )
        policy_id = self.policy(event)
        if policy_id:
            raise Refusal("pack_violation", {"policy_id": policy_id})
        verdict = self.steward.review(deepcopy(event))
        if verdict.action not in {"allow", "redact"}:
            raise Refusal("steward_blocked", {"policy_id": verdict.policy_id})
        result = self._append(tx, event, sender, verdict, now)
        self._cache.apply(result.accepted, verdict.redact)
        self._cache.sync(tx)
        return self._ack(state, result.accepted, result.receipt, sender.participant)

    def _ack(
        self, state: State, event: Document, receipt: Document, viewer: str
    ) -> Acknowledgement:
        redactions = self._cache.redactions.get(event["event_id"], ())
        return Acknowledgement(delivery(state, event, viewer, self.sign, redactions), receipt)

    def _identity(
        self, state: State, event: Document, sender: AuthenticatedSender, host: bool
    ) -> None:
        if host:
            return
        joining = event["type"] == "coalition.join"
        require(joining or sender.participant in state.members, "unknown_participant")
        if joining:
            require(
                self.invitations.get(sender.participant) == sender.card_url
                and sender.participant not in state.members
                and sender.participant not in state.former
                and event["payload"]["card_url"] == sender.card_url
            )
        else:
            require(
                state.members[sender.participant]["sender"] == sender.card_url, "sender_mismatch"
            )
        card = self.cards.get(sender.card_url)
        require(card is not None, "bad_signature")
        assert card is not None
        require(card.participant == sender.participant, "sender_mismatch")
        try:
            verify_envelope(event, card.key, expected_kid=card.kid)
            if joining:
                verify_owner_proof(event, agent_public_key=card.key)
                check_owner_key_unique(
                    {
                        name: jwk_thumbprint(member["owner_key"])
                        for name, member in (state.members | state.former).items()
                    },
                    sender.participant,
                    jwk_thumbprint(event["payload"]["owner_key"]),
                )
            elif event["type"] == "coalition.decide":
                jwk = state.members[sender.participant]["owner_key"]
                verify_consent(
                    self.coalition_id,
                    event["payload"],
                    jwk_to_public_key(jwk),
                    expected_kid=jwk["kid"],
                    participant=sender.participant,
                )
        except OwnerKeyConflictError:
            raise Refusal("not_authorized") from None
        except SignatureError:
            raise Refusal("bad_signature") from None

    def _sources(self, state: State, event: Document, source_ids: list[str]) -> list[Document]:
        ids = set(source_ids)
        if event.get("causation_id"):
            ids.add(event["causation_id"])
        sources: list[Document] = []
        for identifier in ids:
            require(identifier in state.events)
            sources.append(state.events[identifier])
        for identifier in state.task_ids(event):
            if identifier in state.tasks:
                sources.append(state.tasks[identifier]["source"])
        if event["type"] == "coalition.answer" and event["payload"]["query_id"] in state.queries:
            sources.append(state.queries[event["payload"]["query_id"]]["event"])
        redactions = self._cache.redactions
        protected = deepcopy(sources)
        for source in protected:
            extra = redactions.get(source["event_id"], ())
            if extra:
                source["scope"]["redact"] = sorted(
                    set(source["scope"].get("redact", [])) | set(extra)
                )
        return protected

    def _append(
        self,
        tx: Transaction,
        event: Document,
        sender: AuthenticatedSender,
        verdict: Verdict,
        now: str,
    ) -> Acknowledgement[Document]:
        row = tx.execute(
            "SELECT seq, host, created_at FROM coalitions WHERE id = ?", (self.coalition_id,)
        ).fetchone()
        require(row is not None, "unknown_participant")
        sequence = row[0] + 1
        previous = tx.execute(
            "SELECT body FROM events WHERE coalition_id = ? AND seq = ?",
            (self.coalition_id, sequence - 1),
        ).fetchone()
        head = (
            prev_hash(json.loads(previous[0]))
            if previous
            else genesis_hash(self.coalition_id, row[1], row[2])
        )
        accepted = {k: v for k, v in event.items() if k not in HOST_FIELDS}
        accepted.update(seq=sequence, ts=now, prev_hash=head)
        receipt = self.sign(
            "receipt",
            receipt_payload(self.coalition_id, accepted),
            {"audience": "participants", "participants": [sender.participant]},
        )
        tx.execute("UPDATE coalitions SET seq = ? WHERE id = ?", (sequence, self.coalition_id))
        tx.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                self.coalition_id,
                sequence,
                event["event_id"],
                sender.card_url,
                submission_digest(event),
                json.dumps(accepted),
                json.dumps(verdict.redact),
            ),
        )
        tx.execute(
            "INSERT INTO receipts VALUES (?, ?, ?)",
            (self.coalition_id, event["event_id"], json.dumps(receipt)),
        )
        return Acknowledgement(accepted, receipt)

    def _error(
        self, event: Document, sender: AuthenticatedSender, code: str, detail: Document
    ) -> Document:
        ref = event.get("event_id")
        return self.sign(
            "error",
            {"code": code, "detail": detail, "ref": ref if is_ulid(ref) else new_ulid()},
            {"audience": "participants", "participants": [sender.participant]},
        )

    def host_emit(
        self,
        kind: str,
        payload: Document,
        scope: Document | None = None,
        *,
        sources: list[str] | None = None,
        causation_id: str | None = None,
    ) -> Acknowledgement | Document:
        # Revision assignment and validation use the same coalition transaction as append.
        event = self.sign(kind.removeprefix("coalition."), payload, scope or {"audience": "host"})
        sender = AuthenticatedSender(self.card_url, "host")
        try:
            with self._cache.transaction() as tx:
                state = self._cache.refresh(tx, self.clock())
                if causation_id:
                    event["causation_id"] = causation_id
                self._revisions(tx, state, event)
                refs = self._sources(state, event, sources or [])
                if scope is None and refs:
                    event["scope"] = derive_scope(state, refs)
                event["sig"] = sign_envelope(event, self.private_key, self.kid)
                result = self._transaction(tx, event, sender, True, sources or [])
        except Refusal as exc:
            return self._error(event, sender, exc.code, exc.detail)
        except KeyError, TypeError, ValueError:
            return self._error(event, sender, "schema_invalid", {})
        self.bus.publish(self.coalition_id, result.receipt["payload"]["seq"])
        return result

    def _revisions(self, tx: Transaction, state: State, event: Document) -> None:
        body, kind = event["payload"], event["type"]
        objects: list[tuple[str, str, Document]] = []
        if kind == "coalition.charter":
            row = tx.execute(
                "SELECT created_at FROM coalitions WHERE id = ?", (self.coalition_id,)
            ).fetchone()
            body["created_at"] = row[0]
            objects = [("charter", self.coalition_id, body)]
        elif kind == "coalition.tension":
            body.setdefault("tension_id", new_ulid())
            objects = [("tension_option", body["tension_id"], body)]
        elif kind == "coalition.need":
            body.setdefault("need_id", new_ulid())
        elif kind == "coalition.propose":
            for plan in body["plans"]:
                plan.setdefault("plan_id", new_ulid())
                objects.append(("plan", plan["plan_id"], plan))
        for subject_kind, identifier, item in objects:
            old = state.subject(subject_kind, identifier)
            item["revision"] = next_revision(old["revision"]) if old else 1

    def view(self, viewer: str) -> Document:
        with self._cache.transaction() as tx:
            state = self._cache.refresh(tx, self.clock())
            return projection(
                state, list(state.events.values()), viewer, self.sign, self._cache.redactions
            )

    def replay(self, viewer: str, since: int = 0) -> list[Document]:
        with self._cache.transaction() as tx:
            state = self._cache.refresh(tx, self.clock())
            result: list[Document] = []
            for event in state.events.values():
                if event["seq"] > since:
                    result.append(
                        delivery(
                            state,
                            event,
                            viewer,
                            self.sign,
                            self._cache.redactions.get(event["event_id"], ()),
                        )
                        or {
                            "seq": event["seq"],
                            "prev_hash": event["prev_hash"],
                            "hash": prev_hash(event),
                        }
                    )
            return result
