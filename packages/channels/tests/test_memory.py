# SPDX-License-Identifier: Apache-2.0
"""Idempotency memory: time-based expiry, never count-based eviction; full means refuse."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from wa_support import NOW, WA_ID, rig, signed, text_payload

from coalitionkit_channels.whatsapp import WhatsAppError, create_router
from coalitionkit_channels.whatsapp.memory import CapacityExhausted, ExpiringMap


def test_expiring_map_expires_by_time_and_refuses_when_full() -> None:
    now = [0.0]
    m = ExpiringMap[None](ttl=10, capacity=2, clock=lambda: now[0])
    m.put("a", None)
    m.put("b", None)
    with pytest.raises(CapacityExhausted):
        m.put("c", None)  # fails closed: "a" is not evicted
    assert "a" in m and "b" in m
    now[0] = 9.9
    assert "a" in m
    now[0] = 10.1
    assert "a" not in m
    m.put("c", None)


def test_inbound_replay_ids_survive_count_pressure_and_last_the_replay_window() -> None:
    r = rig(memory_capacity=3)
    app = FastAPI()
    app.include_router(create_router(r.channel))
    c = TestClient(app)

    def post(mid: str):
        body, headers = signed(text_payload(WA_ID, "1", mid, r.clock.now))
        return c.post("/webhooks/whatsapp", content=body, headers=headers)

    for n in range(3):
        assert post(f"m{n}").status_code == 200
    assert len(r.channel.receive()) == 3
    assert post("m-new").status_code == 503  # full: refused, nothing evicted
    assert post("m0").status_code == 200  # still known: a replay, deduplicated
    assert r.channel.receive() == []
    # A replay of m0 is refused as stale once its window is over, and its id may then be dropped.
    r.clock.now = NOW + 600 + 300 + 1
    assert post("m-after").status_code == 200
    assert [x.text for x in r.channel.receive()] == ["1"]


def test_outbound_ids_are_remembered_for_the_retry_lifetime_then_expire() -> None:
    r = rig(delivery_memory_seconds=100.0, memory_capacity=2)
    r.channel.send_once("p1", "a", "id-1")
    r.clock.now += 99
    r.channel.send_once("p1", "a", "id-1")  # still remembered: no second send
    assert r.fake.kinds() == ["text"]
    r.clock.now += 2
    r.channel.window.inbound(WA_ID, r.clock.now)
    r.channel.send_once("p1", "a", "id-1")  # expired: this is a new send
    assert r.fake.kinds() == ["text", "text"]


def test_outbound_memory_full_refuses_instead_of_forgetting() -> None:
    r = rig(memory_capacity=2)
    r.channel.send_once("p1", "a", "id-1")
    r.channel.send_once("p1", "b", "id-2")
    sent = len(r.fake.requests)
    with pytest.raises(WhatsAppError):
        r.channel.send_once("p1", "c", "id-3")
    assert len(r.fake.requests) == sent  # nothing went out
    r.channel.send_once("p1", "a", "id-1")  # id-1 was not evicted: still deduplicated
    assert len(r.fake.requests) == sent


def _batch(*items: tuple[str, float]) -> dict[str, object]:
    """One signed-style payload carrying several messages: ``(id, timestamp)`` each."""
    payload = text_payload(WA_ID, "1", "x")
    messages = payload["entry"][0]["changes"][0]["value"]["messages"]
    template = messages[0]
    messages.clear()
    for mid, stamp in items:
        messages.append({**template, "id": mid, "timestamp": str(int(stamp))})
    return payload


def test_one_id_repeated_in_a_batch_takes_room_for_one() -> None:
    r = rig(memory_capacity=2)
    result = r.channel.ingest(_batch(("same", NOW), ("same", NOW), ("same", NOW)))  # pyright: ignore[reportArgumentType]
    assert result.replies == 1 and result.duplicates == 2


def test_duplicates_and_stale_messages_take_no_room() -> None:
    r = rig(memory_capacity=2)
    r.channel.ingest(_batch(("m0", NOW)))  # pyright: ignore[reportArgumentType]
    batch = _batch(("m0", NOW), ("old", NOW - 99999), ("m1", NOW))
    result = r.channel.ingest(batch)  # pyright: ignore[reportArgumentType]
    assert result.duplicates == 1 and result.stale == 1 and result.replies == 1
    with pytest.raises(CapacityExhausted):  # now genuinely full: one new id, no room
        r.channel.ingest(_batch(("m2", NOW)))  # pyright: ignore[reportArgumentType]
