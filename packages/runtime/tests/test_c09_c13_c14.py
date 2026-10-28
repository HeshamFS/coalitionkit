# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

import pytest

from coalitionkit_contracts import (
    LogIntegrityError,
    check_receipts,
    genesis_hash,
    verify_chain,
    verify_receipt,
)
from coalitionkit_runtime import CoalitionHost

from .conftest import NOW, World, accepted, error


def test_c09_concurrent_chain_receipts_and_crash_rebuild(world: World) -> None:
    host = world.host
    before = host.state

    def submit(index: int):
        member = world.alice if index % 2 else world.bob
        return accepted(member.send("observe", {"source": "chat", "content": str(index)}))

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(submit, range(40)))
    entries = world.store.read(host.coalition_id)
    assert verify_chain(entries, genesis_hash(host.coalition_id, host.card_url, NOW)) == len(
        entries
    )
    receipts = [
        verify_receipt(r.receipt, host.private_key.public_key(), accepted=r.accepted)
        for r in results
    ]
    check_receipts(entries, receipts)
    with pytest.raises(LogIntegrityError, match="truncated"):
        check_receipts(entries[:-1], receipts)
    altered = deepcopy(entries)
    altered[-1]["payload"]["content"] = "edited"
    verify_chain(altered, genesis_hash(host.coalition_id, host.card_url, NOW))
    with pytest.raises(LogIntegrityError, match="receipt_mismatch"):
        check_receipts(altered, receipts)
    restored = CoalitionHost(
        world.store, host.coalition_id, host.card_url, host.private_key, host.kid
    )
    assert restored.state == host.state != before


def test_c09_transaction_rollback_and_append_only(world: World) -> None:
    before = world.store.read(world.host.coalition_id)
    with pytest.raises(RuntimeError), world.store.transaction(world.host.coalition_id) as tx:
        tx.execute("UPDATE coalitions SET seq = seq + 1 WHERE id = ?", (world.host.coalition_id,))
        raise RuntimeError("simulated crash")
    result = accepted(world.alice.send("observe", {"source": "chat", "content": "after crash"}))
    assert result.accepted["seq"] == len(before) + 1
    import sqlite3

    with (
        pytest.raises(sqlite3.IntegrityError),
        world.store.transaction(world.host.coalition_id) as tx,
    ):
        tx.execute("DELETE FROM events WHERE coalition_id = ?", (world.host.coalition_id,))


def test_c13_replay_and_duplicate_mismatch(world: World) -> None:
    event = world.alice.envelope("observe", {"source": "chat", "content": "first"})
    first = accepted(world.host.accept(event, world.alice.auth))
    assert world.host.accept(event, world.alice.auth) == first
    event["seq"] = 123
    assert world.host.accept(event, world.alice.auth) == first
    event["payload"]["content"] = "different"
    assert (
        error(world.host.accept(event, world.alice.auth), "duplicate_mismatch")["payload"]["detail"]
        == {}
    )
    other = world.bob.envelope("observe", {"source": "chat", "content": "other"})
    other["event_id"] = event["event_id"]
    assert (
        error(world.host.accept(other, world.bob.auth), "duplicate_mismatch")["payload"]["detail"]
        == {}
    )


def test_c14_sender_and_check_order(world: World) -> None:
    event = world.alice.envelope("observe", {"source": "chat", "content": "hello"})
    error(world.host.accept(event, world.bob.auth), "sender_mismatch")
    error(
        world.host.accept(event, world.bob.auth, extension_activated=False),
        "extension_not_activated",
    )
    event["payload"]["extra"] = "not allowed"
    event["sig"] = "invalid"
    error(world.host.accept(event, world.alice.auth), "schema_invalid")
