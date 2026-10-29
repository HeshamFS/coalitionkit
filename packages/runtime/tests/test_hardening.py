# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coalitionkit_runtime import CoalitionHost
from coalitionkit_runtime.cache import HostCache
from coalitionkit_runtime.consents import ConsentLedger
from coalitionkit_runtime.store import SQLTransaction, Transaction

from .conftest import NOW, World, accepted, error
from .test_r2 import join_body, newcomer


def restored(world: World) -> CoalitionHost:
    host = world.host
    return CoalitionHost(
        world.store,
        host.coalition_id,
        host.card_url,
        host.private_key,
        host.kid,
        clock=lambda: NOW,
    )


def test_unjoined_invitation_and_immutable_pin_survive_restart(world: World) -> None:
    member = newcomer(world)
    world.host.invite(member.auth)
    member.host = restored(world)
    accepted(member.send("join", join_body(member)))
    with pytest.raises(ValueError, match="cannot be replaced"):
        member.host.pin_card(member.auth, Ed25519PrivateKey.generate().public_key(), member.name)
    member.host.pin_card(member.auth, member.agent.public_key(), member.name)
    accepted(member.send("observe", {"source": "chat", "content": "after restart"}))


def test_accept_reads_bounded_event_rows_and_does_not_request_unchanged_consents(
    world: World,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    execute = SQLTransaction.execute
    request = ConsentLedger.request
    rows_read: list[int] = []
    requested: list[str] = []

    class CountingCursor:
        def __init__(self, cursor: Any) -> None:
            self.cursor = cursor

        def fetchone(self) -> Any:
            row = self.cursor.fetchone()
            rows_read.append(int(row is not None))
            return row

        def fetchall(self) -> Any:
            rows = self.cursor.fetchall()
            rows_read.append(len(rows))
            return rows

    def counted(self: SQLTransaction, sql: str, args: Sequence[Any] = ()) -> Any:
        cursor = execute(self, sql, args)
        return (
            CountingCursor(cursor) if sql.startswith("SELECT") and "FROM events" in sql else cursor
        )

    def requested_subject(
        self: ConsentLedger, subject: dict[str, Any], deciders: Sequence[str]
    ) -> None:
        requested.append(subject["id"])
        request(self, subject, deciders)

    monkeypatch.setattr(SQLTransaction, "execute", counted)
    monkeypatch.setattr(ConsentLedger, "request", requested_subject)
    for index in range(120):
        rows_read.clear()
        accepted(world.alice.send("observe", {"source": "chat", "content": str(index)}))
        assert sum(rows_read) <= 2
    assert requested == []
    rows_read.clear()
    world.host.view("alice")
    world.host.replay("alice")
    assert sum(rows_read) == 0
    error(world.alice.decide("charter", world.host.coalition_id), "not_authorized")
    rows_read.clear()
    accepted(world.alice.send("observe", {"source": "chat", "content": "after refusal"}))
    assert sum(rows_read) <= 2


def test_pending_for_is_scoped_and_closes_on_answer_revision_and_expiry(world: World) -> None:
    task = world.need().accepted["payload"]["need_id"]
    plan = world.propose(task).accepted["payload"]["plans"][0]["plan_id"]
    reference = {"kind": "plan", "id": plan, "revision": 1}
    with world.store.transaction(world.host.coalition_id) as tx:
        assert ConsentLedger(tx, world.host.coalition_id).pending_for("alice") == [reference]
        assert ConsentLedger(tx, "another-coalition").pending_for("alice") == []
        assert ConsentLedger(tx, world.host.coalition_id).pending_for("observer") == []
    accepted(world.alice.decide("plan", plan))
    assert world.host.open_consents("alice") == []
    assert restored(world).open_consents("bob") == [reference]
    world.host.clock = lambda: "2026-10-29T12:00:01Z"
    assert world.host.open_consents("bob") == []
    error(world.bob.decide("plan", plan), "deadline_exceeded")


def test_failed_append_never_poisoned_cache(world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    sync = HostCache.sync
    before = world.host.state_document()
    event = world.alice.envelope("observe", {"source": "chat", "content": "retry"})

    def fail_after_apply(self: HostCache, tx: Transaction) -> None:
        sync(self, tx)
        if event["event_id"] in self.state.events:
            raise RuntimeError("commit failed")

    with monkeypatch.context() as patch:
        patch.setattr(HostCache, "sync", fail_after_apply)
        with pytest.raises(RuntimeError, match="commit failed"):
            world.host.accept(event, world.alice.auth)
    assert world.host.state_document() == before
    accepted(world.host.accept(event, world.alice.auth))
    assert world.host.state_document() == restored(world).state_document()


def test_pending_for_current_revision_and_decider_changes(world: World) -> None:
    accepted(world.host.host_emit("charter", world.host.state.charter, {"audience": "coalition"}))
    accepted(world.host.host_emit("charter", world.host.state.charter, {"audience": "coalition"}))
    assert world.host.open_consents("alice") == [
        {"kind": "charter", "id": world.host.coalition_id, "revision": 3}
    ]


def test_read_expiry_does_not_corrupt_catchup_from_another_host(world: World) -> None:
    task = world.need().accepted["payload"]["need_id"]
    plan = world.propose(task).accepted["payload"]["plans"][0]["plan_id"]
    other = restored(world)
    world.host.clock = lambda: "2026-10-29T12:00:01Z"
    assert world.host.open_consents("alice") == []
    accepted(
        other.accept(
            world.alice.envelope("ripple", {"change": "Changed", "invalidates": [task]}),
            world.alice.auth,
        )
    )
    assert world.host.state.subject("plan", plan)["status"] == "superseded"
    assert world.host.state.tasks[task]["status"] == "negotiating"


def test_settled_second_answer_keeps_normative_stage_precedence(world: World) -> None:
    task = world.need().accepted["payload"]["need_id"]
    plan = world.propose(task).accepted["payload"]["plans"][0]["plan_id"]
    accepted(world.alice.decide("plan", plan))
    error(world.alice.decide("plan", plan), "not_authorized")
    accepted(world.bob.decide("plan", plan))
    error(world.alice.decide("plan", plan), "stage_mismatch")
