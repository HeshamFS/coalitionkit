# SPDX-License-Identifier: Apache-2.0
"""Bounded memory that expires by time, never by count: it fails closed when full."""

from __future__ import annotations

import time
from collections.abc import Callable


class CapacityExhausted(Exception):
    """No room for a new entry and nothing has expired yet. The caller must refuse."""


class ExpiringMap[V]:
    """Entries live for ``ttl`` seconds. A full map refuses new keys (it never evicts a live
    one, so an id cannot be forgotten before its time)."""

    def __init__(self, ttl: float, capacity: int, clock: Callable[[], float] = time.time) -> None:
        self._ttl, self._capacity, self._clock = ttl, capacity, clock
        self._items: dict[str, tuple[V, float]] = {}

    def _purge(self) -> None:
        now = self._clock()
        for key in [k for k, (_, until) in self._items.items() if until <= now]:
            del self._items[key]

    def get(self, key: str) -> V | None:
        self._purge()
        item = self._items.get(key)
        return None if item is None else item[0]

    def __contains__(self, key: str) -> bool:
        self._purge()
        return key in self._items

    def has_room(self, new_keys: int) -> bool:
        self._purge()
        return len(self._items) + new_keys <= self._capacity

    def put(self, key: str, value: V) -> None:
        """Set ``key`` (renewing its time). Raises ``CapacityExhausted`` for a new key when full."""
        self._purge()
        if key not in self._items and len(self._items) >= self._capacity:
            raise CapacityExhausted
        self._items[key] = (value, self._clock() + self._ttl)
