# SPDX-License-Identifier: Apache-2.0
"""Viewers that follow a Coalition through the bus, and the log checks the scenarios share."""

from __future__ import annotations

from coalitionkit_contracts import genesis_hash, verify_chain
from coalitionkit_runtime import CoalitionHost, SubscriberDropped, Subscription

from .arena import NOW


class Viewer:
    """A subscriber that keeps every event it is given, by sequence number."""

    def __init__(self, host: CoalitionHost, name: str, since: int = 0) -> None:
        self.host = host
        self.name = name
        self.cursor = since
        self.seen: list[int] = []
        self.dropped = 0
        self._subscription: Subscription | None = host.bus.subscribe(host.coalition_id, since)

    def pump(self) -> int:
        """Read what is new from the cursor. A dropped subscription reconnects at the cursor."""
        if self._subscription is None:
            self.reconnect()
        assert self._subscription is not None
        try:
            fresh = self._subscription.read(self.host.store)
        except SubscriberDropped:
            self.dropped += 1
            self.reconnect()
            assert self._subscription is not None
            fresh = self._subscription.read(self.host.store)
        self.seen.extend(event["seq"] for event in fresh)
        self.cursor = self._subscription.cursor
        return len(fresh)

    def disconnect(self) -> None:
        """Go away mid-way: the cursor stays where the viewer last read."""
        if self._subscription is not None:
            self.host.bus.unsubscribe(self._subscription)
            self._subscription = None

    def reconnect(self) -> None:
        self.disconnect()
        self._subscription = self.host.bus.subscribe(self.host.coalition_id, self.cursor)

    def lost(self, head: int) -> int:
        """Events up to ``head`` this viewer never received, plus any it received twice."""
        expected = set(range(1, head + 1))
        got = set(self.seen)
        return len(expected - got) + (len(self.seen) - len(got))


def check_log(host: CoalitionHost) -> int:
    """Verify the genesis, the hash chain and the host signatures; return the event count.

    Raises when an event is missing, duplicated, reordered or edited.
    """
    created = host.store.read(host.coalition_id)
    seqs = [event["seq"] for event in created]
    if seqs != list(range(1, len(seqs) + 1)):
        raise AssertionError(f"sequence numbers are not contiguous: {seqs[:5]}...")
    ids = [event["event_id"] for event in created]
    if len(set(ids)) != len(ids):
        raise AssertionError("an event is stored twice")
    replay = host.replay("host")
    genesis = genesis_hash(host.coalition_id, host.card_url, _created_at(host))
    return verify_chain(replay, genesis, host.private_key.public_key())


def _created_at(host: CoalitionHost) -> str:
    charter = host.state.charter
    return str(charter.get("created_at", NOW))
