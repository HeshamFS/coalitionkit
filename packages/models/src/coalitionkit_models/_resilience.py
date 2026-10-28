# SPDX-License-Identifier: Apache-2.0
"""Retry with backoff and per-key rate limiting, shared by the chat gateway and media client."""

from __future__ import annotations

import asyncio
import random
import time
from collections import deque
from collections.abc import Awaitable, Callable
from typing import Any

from .errors import ProviderError

RETRYABLE_STATUS = frozenset({408, 409, 429})

#: Decides about one failure: ``(is_transient, http_status_or_None)``.
Classifier = Callable[[Exception], tuple[bool, int | None]]


def transient_status(status: int) -> bool:
    return status in RETRYABLE_STATUS or status >= 500


class RateLimiter:
    """At most ``per_minute`` requests in any 60 second window; waits instead of failing."""

    def __init__(
        self,
        per_minute: int,
        clock: Callable[[], float],
        sleep: Callable[[float], Awaitable[None]],
    ) -> None:
        self._per_minute = per_minute
        self._clock = clock
        self._sleep = sleep
        self._stamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = self._clock()
                while self._stamps and now - self._stamps[0] >= 60.0:
                    self._stamps.popleft()
                if len(self._stamps) < self._per_minute:
                    self._stamps.append(now)
                    return
                await self._sleep(60.0 - (now - self._stamps[0]))


class Retrier:
    """Exponential backoff with full jitter, a rate limiter per key, never retries a 4xx."""

    def __init__(
        self,
        max_attempts: int,
        *,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], float] = time.monotonic,
        rng: random.Random | None = None,
        base_delay_s: float = 0.5,
        max_delay_s: float = 8.0,
    ) -> None:
        self._attempts = max_attempts
        self._sleep = sleep
        self._clock = clock
        self._rng = rng or random.Random()
        self._base = base_delay_s
        self._max = max_delay_s
        self._limiters: dict[str, RateLimiter] = {}

    def limiter(self, key: str, per_minute: int) -> RateLimiter:
        limiter = self._limiters.get(key)
        if limiter is None:
            limiter = RateLimiter(per_minute, self._clock, self._sleep)
            self._limiters[key] = limiter
        return limiter

    def backoff(self, attempt: int) -> float:
        """Full jitter: a random delay up to the capped exponential."""
        return self._rng.uniform(0.0, min(self._max, self._base * 2**attempt))

    async def run[T](
        self, key: str, per_minute: int, call: Callable[[], Awaitable[T]], classify: Classifier
    ) -> T:
        """Run ``call`` under the key's rate limit; raise ProviderError when it fails for good."""
        for attempt in range(self._attempts):
            await self.limiter(key, per_minute).acquire()
            try:
                return await call()
            except Exception as exc:
                transient, status = classify(exc)
                last = attempt + 1 >= self._attempts
                if not transient or last:
                    raise _provider_error(exc, status, attempt + 1) from exc
                await self._sleep(self.backoff(attempt))
        raise AssertionError("unreachable")  # pragma: no cover


def _provider_error(exc: Exception, status: int | None, attempts: int) -> ProviderError:
    detail: Any = type(exc).__name__
    return ProviderError(f"{detail} after {attempts} attempt(s)", status=status, attempts=attempts)
