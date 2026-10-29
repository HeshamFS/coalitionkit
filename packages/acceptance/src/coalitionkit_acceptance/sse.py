# SPDX-License-Identifier: Apache-2.0
"""SSE viewers on ``/v1/feed``, run on their own event loop so arrival times are not skewed.

A viewer applies the first snapshot and every state delta it receives, keeps the time each frame
arrived, and can be disconnected and reconnected like a browser tab.
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
from collections.abc import Coroutine
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

import httpx

from coalitionkit_surfaces.frames import apply_patch

Document = dict[str, Any]


@dataclass
class Arrival:
    at: float
    kind: str
    ops: list[Document]


@dataclass
class FeedViewer:
    name: str
    base: str
    token: str
    state: Document = field(default_factory=lambda: Document())
    arrivals: list[Arrival] = field(default_factory=lambda: list[Arrival]())
    snapshots: int = 0
    errors: list[str] = field(default_factory=lambda: list[str]())
    task: asyncio.Task[None] | None = None
    connected: threading.Event = field(default_factory=threading.Event)

    def event_ids(self) -> set[str]:
        return set(self.state.get("events", {}))

    def deltas_after(self, moment: float) -> list[Arrival]:
        return [a for a in list(self.arrivals) if a.kind == "STATE_DELTA" and a.at >= moment]

    async def run(self, http: httpx.AsyncClient) -> None:
        try:
            async with http.stream(
                "GET",
                self.base + "/v1/feed",
                headers={"Authorization": "Bearer " + self.token},
                timeout=httpx.Timeout(None, connect=30),
            ) as response:
                if response.status_code != 200:
                    self.errors.append(f"status {response.status_code}")
                    return
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        self.take(json.loads(line[6:]))
        except (httpx.HTTPError, OSError) as exc:
            self.errors.append(type(exc).__name__)

    def take(self, frame: Document) -> None:
        now = time.perf_counter()
        kind = frame["type"]
        if kind == "STATE_SNAPSHOT":
            self.state = deepcopy(frame["snapshot"])
            self.snapshots += 1
            self.connected.set()
        elif kind == "STATE_DELTA":
            self.state = apply_patch(self.state, frame["delta"])
            self.arrivals.append(Arrival(now, kind, frame["delta"]))
        elif kind == "RUN_ERROR":
            self.errors.append(str(frame.get("code")))


class ViewerPool:
    """A thread with an event loop that holds many feed viewers."""

    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()
        self.http: httpx.AsyncClient = self.call(self._client())
        self.viewers: dict[str, FeedViewer] = {}
        self.closed = False

    def call[T](self, work: Coroutine[Any, Any, T], timeout: float = 120.0) -> T:
        return asyncio.run_coroutine_threadsafe(work, self.loop).result(timeout)

    @staticmethod
    async def _client() -> httpx.AsyncClient:
        return httpx.AsyncClient(
            limits=httpx.Limits(max_connections=None, max_keepalive_connections=0)
        )

    def add(self, key: str, name: str, base: str, token: str, wait: float = 60.0) -> FeedViewer:
        viewer = FeedViewer(name, base, token)
        self.viewers[key] = viewer

        async def start() -> None:
            viewer.task = asyncio.create_task(viewer.run(self.http))

        self.call(start())
        if not viewer.connected.wait(wait):
            raise RuntimeError(f"viewer {key} got no snapshot: {viewer.errors}")
        return viewer

    def disconnect(self, key: str) -> None:
        viewer = self.viewers[key]

        async def stop() -> None:
            if viewer.task is not None:
                viewer.task.cancel()
                await asyncio.gather(viewer.task, return_exceptions=True)

        self.call(stop())
        viewer.connected.clear()

    def reconnect(self, key: str, wait: float = 60.0) -> FeedViewer:
        old = self.viewers[key]
        return self.add(key, old.name, old.base, old.token, wait)

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        for key in list(self.viewers):
            self.disconnect(key)
        self.call(self.http.aclose())
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(15)
        self.loop.close()
