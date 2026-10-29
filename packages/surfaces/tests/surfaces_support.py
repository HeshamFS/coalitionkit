# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from collections.abc import Generator, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coalitionkit_contracts import new_ulid, public_key_to_jwk, sign_envelope, sign_owner_proof
from coalitionkit_runtime import Acknowledgement, AuthenticatedSender, CoalitionHost, SQLiteStore
from coalitionkit_surfaces import SurfaceHub, load_catalog
from coalitionkit_surfaces.fakes import FakeClock, FakeOwnerSigner, FakeViewerAuth
from coalitionkit_surfaces.frames import Frame, KeepAlive

NOW = "2026-10-28T12:00:00+00:00"
PUBLIC: dict[str, Any] = {"audience": "coalition"}
FIXTURE = Path(__file__).parent / "fixtures" / "catalog.json"


def ok(result: Acknowledgement | dict[str, Any]) -> Acknowledgement[dict[str, Any]]:
    assert isinstance(result, Acknowledgement), result
    return cast(Acknowledgement[dict[str, Any]], result)


@dataclass
class Person:
    host: CoalitionHost
    name: str
    agent: Ed25519PrivateKey = field(default_factory=Ed25519PrivateKey.generate)
    owner: Ed25519PrivateKey = field(default_factory=Ed25519PrivateKey.generate)

    @property
    def auth(self) -> AuthenticatedSender:
        return AuthenticatedSender(f"https://{self.name}.example/card", self.name)

    @property
    def signer(self) -> FakeOwnerSigner:
        return FakeOwnerSigner(
            self.host.coalition_id,
            self.name,
            self.auth.card_url,
            self.agent,
            self.name,
            self.owner,
            self.name + "-owner",
        )

    def send(self, kind: str, body: dict[str, Any]) -> Acknowledgement | dict[str, Any]:
        event: dict[str, Any] = {
            "ext_version": "0.1",
            "coalition_id": self.host.coalition_id,
            "event_id": new_ulid(),
            "type": f"coalition.{kind}",
            "sender": self.auth.card_url,
            "on_behalf_of": self.name,
            "scope": PUBLIC,
            "payload": body,
        }
        event["sig"] = sign_envelope(event, self.agent, self.name)
        return self.host.accept(event, self.auth)

    def join(self) -> None:
        self.host.pin_card(self.auth, self.agent.public_key(), self.name)
        self.host.invite(self.auth)
        jwk = public_key_to_jwk(self.owner.public_key(), self.name + "-owner")
        proof = sign_owner_proof(
            self.host.coalition_id, self.name, self.auth.card_url, jwk, self.owner
        )
        ok(
            self.send(
                "join",
                {
                    "card_url": self.auth.card_url,
                    "owner_key": jwk,
                    "owner_proof": proof,
                    "roles_requested": ["member"],
                    "surfaces": [],
                    "vault": "local",
                },
            )
        )
        subject = {
            "kind": "charter",
            "id": self.host.coalition_id,
            "revision": self.host.state.charter["revision"],
        }
        envelope = self.signer.sign_decision(subject, self.host.coalition_id, True)
        ok(self.host.accept(envelope, self.auth))


@dataclass
class World:
    host: CoalitionHost
    store: SQLiteStore
    alice: Person
    bob: Person
    carol: Person

    def emit(
        self, kind: str, body: dict[str, Any], scope: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return ok(self.host.host_emit(kind, body, scope or PUBLIC)).accepted

    def need(
        self, scope: dict[str, Any] | None = None, window: str = "2026-10-29T12:00:00Z"
    ) -> str:
        body: dict[str, Any] = {
            "description": "Shared task",
            "requirements": [],
            "window": {"start": NOW, "end": window},
        }
        return self.emit("need", body, scope)["payload"]["need_id"]

    def propose(self, task: str, assignees: list[str]) -> str:
        plans: list[dict[str, Any]] = [
            {"assignments": [{"task_id": task, "assignee": a}], "objective_scores": {}}
            for a in assignees
        ]
        body: dict[str, Any] = {
            "proposal_set_id": new_ulid(),
            "decision_deadline": "2026-10-29T12:00:00Z",
            "plans": plans,
        }
        return self.emit("propose", body)["payload"]["plans"][0]["plan_id"]


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
    ok(
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
    people = [Person(host, n) for n in ("alice", "bob", "carol")]
    for person in people:
        person.join()
    yield World(host, store, *people)
    store.close()


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def hub(world: World, clock: FakeClock) -> SurfaceHub:
    people = {p.name: p for p in (world.alice, world.bob, world.carol)}
    auth = FakeViewerAuth({f"tok-{n}": n for n in people})
    return SurfaceHub(
        world.host,
        auth,
        lambda viewer: people[viewer].signer,
        catalog=load_catalog(FIXTURE),
        clock=clock,
        sleep=_no_sleep,
        max_ticks=1,
    )


async def _no_sleep(_: float) -> None:
    return None


def ops_of(frame: Any) -> list[dict[str, Any]]:
    """The patch operations of a STATE_DELTA exactly as they go on the wire."""
    return json.loads(frame.model_dump_json(by_alias=True))["delta"]


def dump(frames: Sequence[Frame]) -> str:
    """The JSON of every AG-UI event in ``frames`` (keep-alive comments carry no data)."""
    return "".join(f.model_dump_json() for f in frames if not isinstance(f, KeepAlive))
