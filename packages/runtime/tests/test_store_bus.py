# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coalitionkit_contracts import genesis_hash, new_ulid, verify_chain
from coalitionkit_runtime import Bus, CoalitionHost, PostgresStore, SubscriberDropped

from .conftest import NOW, PUBLIC, World, accepted, join


def test_bus_wakes_then_reads_and_drops_slow_subscribers(world: World) -> None:
    bus = world.host.bus
    sub = bus.subscribe(world.host.coalition_id, len(world.store.read(world.host.coalition_id)))
    event = accepted(world.alice.send("observe", {"source": "chat", "content": "wake"}))
    assert sub.wake.wait(0.1)
    assert sub.read(world.store) == [event.accepted]
    assert not sub.wake.is_set()
    bus.publish(world.host.coalition_id, sub.cursor + 1001)
    assert sub.dropped
    with pytest.raises(SubscriberDropped):
        sub.read(world.store)
    resumed = bus.subscribe(world.host.coalition_id, sub.cursor)
    assert resumed.read(world.store) == []
    bus.unsubscribe(resumed)


@pytest.mark.requires_db
@pytest.mark.skipif(
    not os.environ.get("COALITIONKIT_TEST_DATABASE_URL"), reason="database URL unset"
)
def test_c09_postgres_concurrent_writers_and_rollback() -> None:
    store = PostgresStore(os.environ["COALITIONKIT_TEST_DATABASE_URL"])
    host = CoalitionHost(
        store,
        new_ulid(),
        "https://host.example/card",
        Ed25519PrivateKey.generate(),
        "host",
        clock=lambda: NOW,
        bus=Bus(),
    )
    try:
        host.create()
        accepted(
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
        alice = join(host, "alice")
        with pytest.raises(RuntimeError), store.transaction(host.coalition_id) as tx:
            tx.execute("UPDATE coalitions SET seq = seq + 1 WHERE id = ?", (host.coalition_id,))
            raise RuntimeError("rollback")
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [
                pool.submit(alice.send, "observe", {"source": "chat", "content": str(i)})
                for i in range(20)
            ]
            for future in futures:
                accepted(future.result())
        entries = store.read(host.coalition_id)
        assert verify_chain(
            entries,
            genesis_hash(host.coalition_id, host.card_url, NOW),
            host.private_key.public_key(),
        ) == len(entries)
    finally:
        store.close()


def test_c09_sqlite_file_reopen_and_independent_connections(world: World) -> None:
    from pathlib import Path
    from tempfile import TemporaryDirectory

    from coalitionkit_runtime import SQLiteStore

    with TemporaryDirectory(dir=Path(__file__).parent) as directory:
        path = str(Path(directory) / "events.sqlite")
        first_store = SQLiteStore(path)
        first = CoalitionHost(
            first_store,
            new_ulid(),
            world.host.card_url,
            world.host.private_key,
            "host",
            clock=lambda: NOW,
        )
        first.create()
        accepted(first.host_emit("charter", world.host.state.charter, PUBLIC))
        alice = join(first, "alice")
        snapshot = first.state_document()
        first_store.close()
        reopened = SQLiteStore(path)
        second_store = SQLiteStore(path)
        try:
            restored = CoalitionHost(
                reopened,
                first.coalition_id,
                first.card_url,
                first.private_key,
                "host",
                clock=lambda: NOW,
            )
            concurrent = CoalitionHost(
                second_store,
                first.coalition_id,
                first.card_url,
                first.private_key,
                "host",
                clock=lambda: NOW,
            )
            assert restored.state_document() == snapshot
            with ThreadPoolExecutor(max_workers=4) as pool:
                futures = [
                    pool.submit(
                        (restored if i % 2 else concurrent).accept,
                        alice.envelope("observe", {"source": "chat", "content": str(i)}),
                        alice.auth,
                    )
                    for i in range(20)
                ]
                for future in futures:
                    accepted(future.result())
            entries = reopened.read(first.coalition_id)
            assert (
                verify_chain(
                    entries,
                    genesis_hash(first.coalition_id, first.card_url, NOW),
                    first.private_key.public_key(),
                )
                == 23
            )
            assert restored.state_document() == concurrent.state_document()
        finally:
            reopened.close()
            second_store.close()


def test_a_subscriber_whose_loop_closed_neither_breaks_publish_nor_starves_the_others() -> None:
    import asyncio

    from coalitionkit_runtime.bus import Bus

    bus = Bus()
    loop = asyncio.new_event_loop()
    loop.close()

    def notify() -> None:
        loop.call_soon_threadsafe(lambda: None)

    dead = bus.subscribe("c", 0, notify)
    others = [bus.subscribe("c", 0) for _ in range(20)]
    bus.publish("c", 1)  # the event is stored already: publishing must not raise
    assert all(s.wake.is_set() for s in others)
    assert dead.dropped
