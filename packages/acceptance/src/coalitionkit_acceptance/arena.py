# SPDX-License-Identifier: Apache-2.0
"""Scripted participants and a Coalition around an in-process ``CoalitionHost``."""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, cast

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coalitionkit_contracts import (
    new_ulid,
    public_key_to_jwk,
    sign_consent,
    sign_envelope,
    sign_owner_proof,
)
from coalitionkit_runtime import Acknowledgement, AuthenticatedSender, CoalitionHost, EventStore

Document = dict[str, Any]
Reply = Acknowledgement | Document

NOW = "2026-10-28T12:00:00+00:00"
DEADLINE = "2026-10-29T12:00:00Z"
PUBLIC: Document = {"audience": "coalition"}
HOST_CARD = "https://host.example/card"


class Refused(AssertionError):
    """A scripted step the host refused when the script expected it to be accepted."""

    def __init__(self, code: str, reply: Document) -> None:
        super().__init__(f"host refused with {code}: {reply}")
        self.code = code


def accepted(reply: object) -> Acknowledgement[Document]:
    if isinstance(reply, Acknowledgement):
        return cast("Acknowledgement[Document]", reply)
    doc = cast(Document, reply)
    raise Refused(str(doc.get("payload", {}).get("code")), doc)


def refusal_code(reply: object) -> str | None:
    """The protocol error code of a refusal, or None when the reply is an acknowledgement."""
    if isinstance(reply, Acknowledgement):
        return None
    return str(cast(Document, reply).get("payload", {}).get("code"))


@dataclass
class Participant:
    """A scripted agent with its own agent key and its owner's key."""

    host: CoalitionHost
    name: str
    agent: Ed25519PrivateKey = field(default_factory=Ed25519PrivateKey.generate)
    owner: Ed25519PrivateKey = field(default_factory=Ed25519PrivateKey.generate)
    #: Called with the seconds each submission took, when a scenario wants latencies.
    timer: Callable[[float], None] | None = None

    def submit(self, envelope: Document) -> Reply:
        start = time.perf_counter()
        try:
            return self.host.accept(envelope, self.auth)
        finally:
            if self.timer is not None:
                self.timer(time.perf_counter() - start)

    @property
    def auth(self) -> AuthenticatedSender:
        return AuthenticatedSender(f"https://{self.name}.example/card", self.name)

    @property
    def coalition_id(self) -> str:
        return self.host.coalition_id

    def envelope(self, kind: str, body: Document, scope: Document | None = None) -> Document:
        event: Document = {
            "ext_version": "0.1",
            "coalition_id": self.coalition_id,
            "event_id": new_ulid(),
            "type": f"coalition.{kind}",
            "sender": self.auth.card_url,
            "on_behalf_of": self.name,
            "scope": scope or PUBLIC,
            "payload": body,
        }
        event["sig"] = sign_envelope(event, self.agent, self.name)
        return event

    def send(self, kind: str, body: Document, scope: Document | None = None) -> Reply:
        return self.submit(self.envelope(kind, body, scope))

    def join_body(self) -> Document:
        jwk = public_key_to_jwk(self.owner.public_key(), self.name + "-owner")
        return {
            "card_url": self.auth.card_url,
            "owner_key": jwk,
            "owner_proof": sign_owner_proof(
                self.coalition_id, self.name, self.auth.card_url, jwk, self.owner
            ),
            "roles_requested": ["member"],
            "surfaces": [],
            "vault": "local",
        }

    def decision(
        self,
        kind: str,
        subject: str,
        revision: int,
        choice: str | None = None,
        consent: bool = True,
    ) -> Document:
        body: Document = {
            "subject": {"kind": kind, "id": subject, "revision": revision},
            "choice": choice or subject,
            "consent": consent,
            "decided_at": NOW,
        }
        body["consent_sig"] = sign_consent(
            self.coalition_id, body, self.owner, self.name + "-owner", participant=self.name
        )
        return body

    def decision_envelope(
        self, kind: str, subject: str, revision: int = 1, choice: str | None = None
    ) -> Document:
        return self.envelope("decide", self.decision(kind, subject, revision, choice))

    def decide(
        self, kind: str, subject: str, revision: int = 1, choice: str | None = None
    ) -> Reply:
        return self.submit(self.decision_envelope(kind, subject, revision, choice))

    def observe_envelope(self, content: str) -> Document:
        return self.envelope("observe", {"source": "chat", "content": content})

    def offer_envelope(
        self, task: str, minutes: int, money: int, offer_id: str | None = None
    ) -> Document:
        body: Document = {
            "offer_id": offer_id or f"{self.name}-{task}",
            "target": {"kind": "need", "id": task},
            "capacity": 1,
            "cost": {"minutes": minutes, "money": money, "effort": "low"},
            "valid_until": DEADLINE,
        }
        return self.envelope("offer", body)

    def offer(self, task: str, minutes: int, money: int, offer_id: str | None = None) -> Reply:
        return self.submit(self.offer_envelope(task, minutes, money, offer_id))


def make_host(
    store: EventStore,
    coalition_id: str | None = None,
    host_key: Ed25519PrivateKey | None = None,
    card_url: str = HOST_CARD,
) -> CoalitionHost:
    return CoalitionHost(
        store,
        coalition_id or new_ulid(),
        card_url,
        host_key or Ed25519PrivateKey.generate(),
        "host",
        clock=lambda: NOW,
    )


class Arena:
    """One Coalition: a host, its store and the scripted members who joined it."""

    def __init__(self, host: CoalitionHost, deciders: Sequence[str]) -> None:
        self.host = host
        self.deciders = list(deciders)
        self.members: dict[str, Participant] = {}
        self.timer: Callable[[float], None] | None = None

    @classmethod
    def open(
        cls,
        store: EventStore,
        deciders: Sequence[str],
        *,
        coalition_id: str | None = None,
        host_key: Ed25519PrivateKey | None = None,
        card_url: str = HOST_CARD,
    ) -> Arena:
        """Create the Coalition in the store and publish its charter."""
        arena = cls(make_host(store, coalition_id, host_key, card_url), deciders)
        arena.host.create()
        charter: Document = {
            "goal": "Coordinate",
            "roles": [{"id": "member"}],
            "rules": [],
            "deadline": DEADLINE,
            "deciders": list(deciders),
        }
        accepted(arena.host.host_emit("charter", charter, PUBLIC))
        return arena

    def enroll(self, name: str, *, accept_charter: bool = True) -> Participant:
        person = Participant(self.host, name, timer=self.timer)
        self.members[name] = person
        self.attach(person)
        accepted(person.send("join", person.join_body()))
        if accept_charter:
            revision = self.host.state.charter["revision"]
            accepted(person.decide("charter", self.host.coalition_id, revision))
        return person

    def attach(self, person: Participant) -> None:
        """Pin the member's card key and record its invitation (the edge does this in real use)."""
        self.host.pin_card(person.auth, person.agent.public_key(), person.name)
        self.host.invite(person.auth)

    def restarted(self, store: EventStore, host_key: Ed25519PrivateKey) -> Arena:
        """A new host over the same Coalition in ``store``, with every member re-attached.

        Pinned cards and invitations live in host memory, so a restarted host gets them again
        from the scripted adapter (the A2A edge does this from card verification in real use).
        """
        host = make_host(store, self.host.coalition_id, host_key, self.host.card_url)
        arena = Arena(host, self.deciders)
        for name, person in self.members.items():
            moved = Participant(host, name, person.agent, person.owner, self.timer)
            arena.members[name] = moved
            arena.attach(moved)
        return arena

    def need(self, task: str | None = None) -> str:
        identifier = task or new_ulid()
        body: Document = {
            "need_id": identifier,
            "description": "Shared task",
            "requirements": [],
            "window": {"start": NOW, "end": DEADLINE},
        }
        accepted(self.host.host_emit("need", body, PUBLIC))
        return identifier

    def propose(self, assignments: dict[str, str], plans: int = 1) -> list[str]:
        """Publish ``plans`` plans over the same assignments; return their IDs."""
        pairs = [{"task_id": t, "assignee": a} for t, a in sorted(assignments.items())]
        listed = [
            {"assignments": pairs, "objective_scores": {"variant": float(index)}}
            for index in range(plans)
        ]
        body: Document = {
            "proposal_set_id": new_ulid(),
            "decision_deadline": DEADLINE,
            "plans": listed,
        }
        reply = accepted(self.host.host_emit("propose", body, PUBLIC))
        return [plan["plan_id"] for plan in reply.accepted["payload"]["plans"]]

    def decide_all(self, kind: str, subject: str, revision: int = 1) -> None:
        for name in self.deciders:
            accepted(self.members[name].decide(kind, subject, revision))

    def close(self) -> None:
        """Release the store's connection (the scenarios turn unclosed ones into errors)."""
        close = getattr(self.host.store, "close", None)
        if callable(close):
            close()

    def events(self) -> list[Document]:
        return self.host.store.read(self.host.coalition_id)
