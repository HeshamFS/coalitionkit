# SPDX-License-Identifier: Apache-2.0
"""The hub ties a host to its viewers' sessions and drives the SSE streams."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import suppress
from typing import Any, Protocol

from coalitionkit_contracts import new_ulid
from coalitionkit_runtime import CoalitionHost, SubscriberDropped, Subscription

from .agent import AgentSession
from .catalog import Catalog
from .feed import FeedSession
from .frames import Frame, encode
from .ports import OwnerSigner, ViewerAuth


class Session(Protocol):
    def start(self) -> list[Frame]: ...
    def changed(self) -> list[Frame]: ...
    def tick(self) -> list[Frame]: ...
    def fail(self, message: str, code: str | None = None) -> list[Frame]: ...


def latest_seq(host: CoalitionHost) -> int:
    events = host.store.read(host.coalition_id)
    return events[-1]["seq"] if events else 0


class SurfaceHub:
    def __init__(
        self,
        host: CoalitionHost,
        auth: ViewerAuth,
        signer_for: Callable[[str], OwnerSigner],
        *,
        catalog: Catalog | None = None,
        clock: Callable[[], float] = time.monotonic,
        new_id: Callable[[], str] = new_ulid,
        sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep,
        poll_interval: float = 0.5,
        max_ticks: int | None = None,
    ) -> None:
        self.host, self.auth, self.signer_for, self.catalog = host, auth, signer_for, catalog
        self.clock, self.new_id, self.sleep = clock, new_id, sleep
        self.poll_interval, self.max_ticks = poll_interval, max_ticks
        self.outboxes: dict[str, deque[str]] = {}
        self.feeds: dict[str, list[FeedSession]] = {}

    # -- what the rest of the system calls ---------------------------------------------------

    def say(self, viewer: str, text: str) -> None:
        """An agent-to-person message, delivered on that person's agent session only."""
        self.outboxes.setdefault(viewer, deque()).append(text)

    def step_started(self, viewer: str, name: str) -> None:
        for session in self.feeds.get(viewer, []):
            session.step_started(name)

    def step_finished(self, viewer: str, name: str) -> None:
        for session in self.feeds.get(viewer, []):
            session.step_finished(name)

    def feed_session(self, viewer: str) -> FeedSession:
        return FeedSession(
            self.host, viewer, clock=self.clock, new_id=self.new_id, catalog=self.catalog
        )

    def agent_session(self, viewer: str) -> AgentSession:
        return AgentSession(
            self.host,
            viewer,
            self.signer_for(viewer),
            clock=self.clock,
            new_id=self.new_id,
            outbox=self.outboxes.setdefault(viewer, deque()),
        )

    # -- streams -----------------------------------------------------------------------------

    async def stream(self, session: Session, viewer: str | None = None) -> AsyncGenerator[str]:
        """SSE text for one connection. Subscribes before the first snapshot so nothing is lost."""
        bus = self.host.bus
        loop = asyncio.get_running_loop()
        wake = asyncio.Event()

        def notify() -> None:
            loop.call_soon_threadsafe(wake.set)

        sub: Subscription = bus.subscribe(
            self.host.coalition_id,
            await asyncio.to_thread(latest_seq, self.host),
            notify,
        )
        registered = isinstance(session, FeedSession) and viewer is not None
        if registered and viewer is not None and isinstance(session, FeedSession):
            self.feeds.setdefault(viewer, []).append(session)
        try:
            try:
                for frame in await asyncio.to_thread(session.start):
                    yield encode(frame)
                ticks = 0
                while self.max_ticks is None or ticks < self.max_ticks:
                    if self.sleep is asyncio.sleep:
                        with suppress(TimeoutError):
                            await asyncio.wait_for(wake.wait(), timeout=self.poll_interval)
                        wake.clear()
                    else:
                        await self.sleep(self.poll_interval)
                    ticks += 1
                    frames = await asyncio.to_thread(self._poll, session, sub)
                    for frame in frames:
                        yield encode(frame)
            except SubscriberDropped:
                for frame in session.fail("connection fell behind", "subscriber_dropped"):
                    yield encode(frame)
            except Exception:
                for frame in session.fail("the stream failed", "stream_error"):
                    yield encode(frame)
        finally:
            bus.unsubscribe(sub)
            if registered and viewer is not None and isinstance(session, FeedSession):
                self.feeds[viewer].remove(session)

    def _poll(self, session: Session, sub: Subscription) -> list[Frame]:
        frames: list[Frame] = []
        if sub.wake.is_set():
            sub.read(self.host.store)  # advances the cursor and clears the wake
            frames += session.changed()
        return frames + session.tick()
