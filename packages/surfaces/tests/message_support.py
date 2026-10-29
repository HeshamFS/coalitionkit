# SPDX-License-Identifier: Apache-2.0
"""Fixtures for the message door tests: four neutral members and the real catalog's doors."""

from __future__ import annotations

from collections.abc import Callable, Generator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from surfaces_support import NOW, PUBLIC, Person, ok

from coalitionkit_contracts import new_ulid
from coalitionkit_runtime import CoalitionHost, SQLiteStore
from coalitionkit_surfaces import load_catalog
from coalitionkit_surfaces.catalog import Catalog
from coalitionkit_surfaces.fakes import FakeClock
from coalitionkit_surfaces.message import (
    ConfirmGate,
    Doors,
    HostTreeSource,
    InMemoryChannel,
    MessageDoor,
    host_is_open,
    load_doors,
)

SPEC = Path(__file__).resolve().parents[3] / "spec" / "catalog" / "coalitionkit-v0_9.json"
NAMES = ("p1", "p2", "p3", "p4")
DEADLINE = "2026-10-29T12:00:00Z"


@dataclass
class MsgWorld:
    host: CoalitionHost
    people: dict[str, Person]

    def emit(
        self, kind: str, body: dict[str, Any], scope: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return ok(self.host.host_emit(kind, body, scope or PUBLIC)).accepted

    def need(self, description: str, scope: dict[str, Any] | None = None) -> str:
        body: dict[str, Any] = {
            "description": description,
            "requirements": [],
            "window": {"start": NOW, "end": DEADLINE},
        }
        return self.emit("need", body, scope)["payload"]["need_id"]

    def propose(self, task: str, assignees: list[str]) -> str:
        plans: list[dict[str, Any]] = [
            {"assignments": [{"task_id": task, "assignee": a}], "objective_scores": {}}
            for a in assignees
        ]
        body: dict[str, Any] = {
            "proposal_set_id": new_ulid(),
            "decision_deadline": DEADLINE,
            "plans": plans,
        }
        return self.emit("propose", body)["payload"]["plans"][0]["plan_id"]

    def tension(self, task: str, tension_id: str | None = None) -> str:
        body: dict[str, Any] = {
            "task_ids": [task],
            "options": [
                {"option_id": "a", "summary": "First"},
                {"option_id": "b", "summary": "Second"},
            ],
            "tradeoffs": [],
            "deciders": ["p1", "p2"],
            "decision_deadline": DEADLINE,
        }
        if tension_id:
            body["tension_id"] = tension_id
        return self.emit("tension", body)["payload"]["tension_id"]


@pytest.fixture
def message_world() -> Generator[MsgWorld]:
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
    charter: dict[str, Any] = {
        "goal": "Coordinate",
        "roles": [{"id": "member"}],
        "rules": [],
        "deadline": DEADLINE,
        "deciders": ["p1", "p2"],
    }
    ok(host.host_emit("charter", charter, PUBLIC))
    people = {name: Person(host, name) for name in NAMES}
    for person in people.values():
        person.join()
    yield MsgWorld(host, people)
    store.close()


@pytest.fixture(scope="session")
def catalog() -> Catalog:
    return load_catalog(SPEC)


@pytest.fixture(scope="session")
def doors() -> dict[str, frozenset[str]]:
    return load_doors(SPEC)


@dataclass
class Rig:
    world: MsgWorld
    channel: InMemoryChannel
    clock: FakeClock
    gate: ConfirmGate
    door: MessageDoor


def make_rig(
    world: MsgWorld,
    catalog: Catalog,
    doors: Doors,
    *,
    limit: int = 1000,
    min_interval: float = 30.0,
    ttl: float = 300.0,
    make_code: Callable[[], str] | None = None,
) -> Rig:
    clock = FakeClock()
    channel = InMemoryChannel(now=clock)
    kwargs: dict[str, Any] = {"make_code": make_code} if make_code else {}
    gate = ConfirmGate(host_is_open(world.host), clock=clock, ttl=ttl, **kwargs)
    door = MessageDoor(
        channel,
        HostTreeSource(world.host),
        catalog,
        doors,
        gate,
        clock=clock,
        limit=limit,
        min_interval=min_interval,
        link_base="https://confirm.example/c",
    )
    return Rig(world, channel, clock, gate, door)
