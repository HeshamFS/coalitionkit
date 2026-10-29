# SPDX-License-Identifier: Apache-2.0
"""Per-recipient rate limit and the customer service window, both clock-injectable."""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable


class RateLimiter:
    """At most ``limit`` sends per recipient in any 60 s span."""

    def __init__(self, limit: int, clock: Callable[[], float] = time.monotonic) -> None:
        self._limit, self._clock = limit, clock
        self._hits: dict[str, deque[float]] = {}

    def allow(self, recipient: str) -> bool:
        now = self._clock()
        if len(self._hits) > 1000:
            self._hits = {k: v for k, v in self._hits.items() if v and now - v[-1] < 60.0}
        hits = self._hits.setdefault(recipient, deque())
        while hits and now - hits[0] >= 60.0:
            hits.popleft()
        if len(hits) >= self._limit:
            return False
        hits.append(now)
        return True


class ServiceWindow:
    """Tracks when each recipient last wrote to us. Free text is allowed only while open."""

    def __init__(self, seconds: float, clock: Callable[[], float] = time.time) -> None:
        self._seconds, self._clock = seconds, clock
        self._last: dict[str, float] = {}
        self._opener_sent: set[str] = set()

    def inbound(self, recipient: str, at: float | None = None) -> None:
        """A message from the person arrived (``at`` is Meta's timestamp, never in the future)."""
        now = self._clock()
        stamp = now if at is None else min(at, now)
        self._last[recipient] = max(stamp, self._last.get(recipient, 0.0))
        self._opener_sent.discard(recipient)

    def is_open(self, recipient: str) -> bool:
        last = self._last.get(recipient)
        return last is not None and self._clock() - last < self._seconds

    def opener_pending(self, recipient: str) -> bool:
        return recipient in self._opener_sent

    def mark_opener(self, recipient: str) -> None:
        self._opener_sent.add(recipient)
