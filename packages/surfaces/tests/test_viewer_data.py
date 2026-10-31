# SPDX-License-Identifier: Apache-2.0
import json
from typing import Any

import pytest
from ag_ui.core import StateDeltaEvent, StateSnapshotEvent
from fastapi.testclient import TestClient
from surfaces_support import PUBLIC, Person, World, dump, ok

from coalitionkit_contracts import (
    LogIntegrityError,
    LogStub,
    check_receipts,
    genesis_hash,
    jwk_to_public_key,
    new_ulid,
    verify_chain,
    verify_receipt,
)
from coalitionkit_runtime import CoalitionHost
from coalitionkit_surfaces import SurfaceHub, apply_patch
from coalitionkit_surfaces.app import create_app
from coalitionkit_surfaces.fakes import FakeViewerAuth


def entries(log: dict[str, Any]) -> list[Any]:
    return [
        LogStub(**item) if set(item) == {"seq", "prev_hash", "hash"} else item
        for item in log["entries"]
    ]


def test_log_delivery_receipts_and_delta(world: World, hub: SurfaceHub) -> None:
    feed = hub.feed_session("bob")
    first = feed.start()[1]
    assert isinstance(first, StateSnapshotEvent)
    snapshot = first.snapshot
    world.need({"audience": "participants", "participants": ["alice"]})
    world.need({"audience": "coalition", "redact": ["payload.description"]})
    changed = feed.changed()[0]
    assert isinstance(changed, StateDeltaEvent)
    delta = changed.model_dump()["delta"]
    updated = apply_patch(snapshot, delta)
    assert feed.changed() == []
    assert set(updated["log"]["entries"][-2]) == {"seq", "prev_hash", "hash"}
    for viewer in ("alice", "bob"):
        log = hub.log(viewer)
        key = jwk_to_public_key(log["host_key"])
        chain = entries(log)
        assert verify_chain(
            chain, genesis_hash(log["coalition_id"], log["host_card_url"], log["created_at"]), key
        ) == len(chain)
        check_receipts(chain, [verify_receipt(r, key) for r in log["receipts"]], key)
        assert log["receipts"]
        projected = log["entries"][-1]
        assert projected["type"] == "coalition.projection"
        assert "description" not in projected["payload"]["payload"]
        own_seqs = {
            e["seq"]
            for e in world.store.read(world.host.coalition_id)
            if e["on_behalf_of"] == viewer
        }
        assert {r["payload"]["seq"] for r in log["receipts"]} == own_seqs


@pytest.mark.parametrize("projected", [False, True])
def test_log_waits_for_visible_delivery(world: World, projected: bool) -> None:
    host = CoalitionHost(
        world.store,
        new_ulid(),
        world.host.card_url,
        world.host.private_key,
        world.host.kid,
        clock=world.host.clock,
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
                "deciders": ["alice"],
            },
            PUBLIC,
        )
    )
    alice = Person(host, "alice")
    alice.join()
    hub = SurfaceHub(host, FakeViewerAuth({"tok-alice": "alice"}), lambda _: alice.signer)
    feed = hub.feed_session("alice")
    first = feed.start()[1]
    assert isinstance(first, StateSnapshotEvent)
    held = first.snapshot
    assert [entry["seq"] for entry in held["log"]["entries"]] == [1, 2, 3]
    local = World(host, world.store, alice, world.bob, world.carol)
    for _ in range(2):
        local.need({"audience": "host"})
        assert feed.changed() == []
        fresh = hub.feed_session("alice").start()[1]
        assert isinstance(fresh, StateSnapshotEvent)
        assert fresh.snapshot["log"] == held["log"]
    scope: dict[str, Any] = {"audience": "coalition"}
    if projected:
        scope["redact"] = ["payload.description"]
    local.need(scope)
    changed = feed.changed()
    assert len(changed) == 1
    assert isinstance(changed[0], StateDeltaEvent)
    held = apply_patch(held, changed[0].model_dump()["delta"])
    log = held["log"]
    assert [
        entry["payload"]["source"]["seq"]
        if entry.get("type") == "coalition.projection"
        else entry["seq"]
        for entry in log["entries"]
    ] == [1, 2, 3, 4, 5, 6]
    assert all(set(entry) == {"seq", "prev_hash", "hash"} for entry in log["entries"][3:5])
    assert log["entries"][-1]["type"] == ("coalition.projection" if projected else "coalition.need")
    assert (
        verify_chain(
            entries(log),
            genesis_hash(log["coalition_id"], log["host_card_url"], log["created_at"]),
            jwk_to_public_key(log["host_key"]),
        )
        == 6
    )
    assert feed.changed() == []
    assert log["receipts"] == first.snapshot["log"]["receipts"]
    local.need({"audience": "host"})
    assert feed.changed() == []
    assert len(hub.log("alice")["entries"]) == 6
    local.need()
    later = feed.changed()[0]
    assert isinstance(later, StateDeltaEvent)
    log = apply_patch(held, later.model_dump()["delta"])["log"]
    assert set(log["entries"][-2]) == {"seq", "prev_hash", "hash"}
    assert (
        verify_chain(
            entries(log),
            genesis_hash(log["coalition_id"], log["host_card_url"], log["created_at"]),
            jwk_to_public_key(log["host_key"]),
        )
        == 8
    )


def test_tampered_stored_event_is_visible_to_verifier(world: World, hub: SurfaceHub) -> None:
    hub.log("alice")
    with world.store.transaction(world.host.coalition_id) as tx:
        # Simulate storage corruption below the append-only application boundary.
        tx.execute("DROP TRIGGER events_no_update")
        row = tx.execute(
            "SELECT body FROM events WHERE coalition_id = ? AND seq = 1", (world.host.coalition_id,)
        ).fetchone()
        event = json.loads(row[0])
        event["payload"]["goal"] = "edited"
        tx.execute(
            "UPDATE events SET body = ? WHERE coalition_id = ? AND seq = 1",
            (json.dumps(event), world.host.coalition_id),
        )
    log = hub.log("alice")
    with pytest.raises(LogIntegrityError):
        verify_chain(
            entries(log),
            genesis_hash(log["coalition_id"], log["host_card_url"], log["created_at"]),
            jwk_to_public_key(log["host_key"]),
        )


def test_view_as_intersection_and_auth(world: World, hub: SurfaceHub) -> None:
    world.need({"audience": "participants", "participants": ["alice"]})
    world.need({"audience": "participants", "participants": ["bob"]})
    client = TestClient(create_app(hub))
    assert client.get("/v1/view-as?participant=bob").status_code == 401
    response = client.get(
        "/v1/view-as?participant=bob", headers={"Authorization": "Bearer tok-alice"}
    )
    assert response.status_code == 200
    data = response.json()["messages"][-1]["updateDataModel"]["value"]
    assert data == {"summary": {"seat": "bob", "role": ["member"], "status": "joined"}}
    world.need({"audience": "coalition", "redact": ["payload.description"]})
    messages = hub.view_as("alice", "bob")
    assert "description" not in json.dumps(messages)
    assert "events" in messages[-1]["updateDataModel"]["value"]


def test_refusals_only_sender(hub: SurfaceHub) -> None:
    alice, bob = hub.feed_session("alice"), hub.feed_session("bob")
    alice.start()
    bob.start()
    hub.refused(
        "alice",
        "coalition.offer",
        {"code": "steward_blocked", "detail": {"policy_id": "rule-one", "secret": "NEVER-SEND"}},
    )
    own = dump(alice.changed())
    assert "steward_blocked" in own and "rule-one" in own and "NEVER-SEND" not in own
    assert "steward_blocked" not in dump(bob.changed())
