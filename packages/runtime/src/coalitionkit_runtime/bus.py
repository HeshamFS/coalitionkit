# SPDX-License-Identifier: Apache-2.0
"""Wakeups are hints; subscribers always fetch ordered events from their cursor."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Event, RLock

from .store import Document, EventStore


class SubscriberDropped(Exception):
    """Reconnect with the last consumed seq."""


@dataclass(eq=False)
class Subscription:
    coalition_id: str
    cursor: int
    wake: Event = field(default_factory=Event)
    dropped: bool = False

    def read(self, store: EventStore) -> list[Document]:
        if self.dropped:
            raise SubscriberDropped(self.cursor)
        self.wake.clear()
        events = store.read(self.coalition_id, self.cursor)
        if len(events) > 1000:
            self.dropped = True
            raise SubscriberDropped(self.cursor)
        if events:
            self.cursor = events[-1]["seq"]
        return events


class Bus:
    def __init__(self) -> None:
        self._subscriptions: set[Subscription] = set()
        self._lock = RLock()

    def subscribe(self, coalition_id: str, since: int = 0) -> Subscription:
        subscription = Subscription(coalition_id, since)
        with self._lock:
            self._subscriptions.add(subscription)
        return subscription

    def unsubscribe(self, subscription: Subscription) -> None:
        with self._lock:
            self._subscriptions.discard(subscription)

    def publish(self, coalition_id: str, seq: int) -> None:
        with self._lock:
            for sub in tuple(self._subscriptions):
                if sub.coalition_id == coalition_id:
                    if seq - sub.cursor > 1000:
                        sub.dropped = True
                        self._subscriptions.remove(sub)
                    sub.wake.set()
