# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass

import pytest
from coalitionkit_runtime import Acknowledgement, AuthenticatedSender, CoalitionHost, SQLiteStore
from coalitionkit_runtime.store import Document
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coalitionkit_contracts import (
    new_ulid,
    public_key_to_jwk,
    sign_consent,
    sign_envelope,
    sign_owner_proof,
)

NOW = "2026-10-28T12:00:00+00:00"
PUBLIC: Document = {"audience": "coalition"}


def accepted(result: Acknowledgement | Document) -> Acknowledgement:
    assert isinstance(result, Acknowledgement), result
    return result


def error(result: Acknowledgement | Document, code: str) -> Document:
    assert isinstance(result, dict), result
    assert result["type"] == "coalition.error"
    assert result["payload"]["code"] == code, result
    return result


@dataclass
class Member:
    host: CoalitionHost
    name: str
    agent: Ed25519PrivateKey
    owner: Ed25519PrivateKey

    @property
    def auth(self) -> AuthenticatedSender:
        return AuthenticatedSender(f"https://{self.name}.example/card", self.name)

    def envelope(
        self,
        kind: str,
        body: Document,
        scope: Document | None = None,
        causation_id: str | None = None,
    ) -> Document:
        event: Document = {
            "ext_version": "0.1",
            "coalition_id": self.host.coalition_id,
            "event_id": new_ulid(),
            "type": f"coalition.{kind}",
            "sender": self.auth.card_url,
            "on_behalf_of": self.name,
            "scope": scope or PUBLIC,
            "payload": body,
        }
        if causation_id:
            event["causation_id"] = causation_id
        event["sig"] = sign_envelope(event, self.agent, self.name)
        return event

    def send(
        self,
        kind: str,
        body: Document,
        scope: Document | None = None,
        causation_id: str | None = None,
    ) -> Acknowledgement | Document:
        return self.host.accept(self.envelope(kind, body, scope, causation_id), self.auth)

    def decision(
        self,
        kind: str,
        identifier: str,
        revision: int = 1,
        consent: bool = True,
        choice: str | None = None,
    ) -> Document:
        body: Document = {
            "subject": {"kind": kind, "id": identifier, "revision": revision},
            "choice": choice or identifier,
            "consent": consent,
            "decided_at": NOW,
        }
        body["consent_sig"] = sign_consent(
            self.host.coalition_id, body, self.owner, self.name + "-owner"
        )
        return body

    def decide(
        self, kind: str, identifier: str, revision: int = 1, consent: bool = True
    ) -> Acknowledgement | Document:
        return self.send("decide", self.decision(kind, identifier, revision, consent))


def join(host: CoalitionHost, name: str, accept_charter: bool = True) -> Member:
    member = Member(host, name, Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate())
    host.pin_card(member.auth, member.agent.public_key(), name)
    jwk = public_key_to_jwk(member.owner.public_key(), name + "-owner")
    body = {
        "card_url": member.auth.card_url,
        "owner_key": jwk,
        "owner_proof": sign_owner_proof(
            host.coalition_id, name, member.auth.card_url, jwk, member.owner
        ),
        "roles_requested": ["member"],
        "surfaces": [],
        "vault": "local",
    }
    accepted(member.send("join", body))
    if accept_charter:
        accepted(member.decide("charter", host.coalition_id, host.state.charter["revision"]))
    return member


@dataclass
class World:
    host: CoalitionHost
    store: SQLiteStore
    alice: Member
    bob: Member
    observer: Member

    def need(self, scope: Document | None = None) -> Acknowledgement:
        return accepted(
            self.host.host_emit(
                "need",
                {
                    "description": "Shared task",
                    "requirements": [],
                    "window": {"start": NOW, "end": "2026-10-29T12:00:00Z"},
                },
                scope or PUBLIC,
            )
        )

    def query(self, task: str, owner: str = "alice") -> Acknowledgement:
        return accepted(
            self.host.host_emit(
                "query",
                {"query_id": new_ulid(), "kind": "feasible", "subject": task},
                {"audience": "participants", "participants": [owner]},
            )
        )

    def propose(self, task: str, owner: str = "alice") -> Acknowledgement:
        return accepted(
            self.host.host_emit(
                "propose",
                {
                    "proposal_set_id": new_ulid(),
                    "plans": [
                        {
                            "assignments": [{"task_id": task, "assignee": owner}],
                            "objective_scores": {},
                        }
                    ],
                },
                PUBLIC,
            )
        )

    def committed(self, task: str, member: Member | None = None) -> str:
        member = member or self.alice
        self.query(task, member.name)
        proposal = self.propose(task, member.name)
        plan = proposal.accepted["payload"]["plans"][0]["plan_id"]
        accepted(self.alice.decide("plan", plan))
        accepted(self.bob.decide("plan", plan))
        commitment = new_ulid()
        accepted(
            member.send(
                "commit", {"commitment_id": commitment, "task_id": task, "status": "pending"}
            )
        )
        accepted(member.decide("commitment", commitment))
        return commitment


@pytest.fixture
def world() -> Generator[World]:
    store = SQLiteStore()
    host = CoalitionHost(
        store,
        new_ulid(),
        "https://host.example/card",
        Ed25519PrivateKey.generate(),
        "host",
        clock=lambda: NOW,
    )
    host.create()
    accepted(
        host.host_emit(
            "charter",
            {
                "goal": "Coordinate",
                "roles": [{"id": "member"}],
                "rules": [],
                "deadline": "2026-10-29T12:00:00Z",
                "deciders": ["alice", "bob"],
            },
            PUBLIC,
        )
    )
    result = World(host, store, join(host, "alice"), join(host, "bob"), join(host, "observer"))
    yield result
    store.close()


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "requires_db: requires COALITIONKIT_TEST_DATABASE_URL")
