# SPDX-License-Identifier: Apache-2.0
"""Compare full folds with incremental feeds; this is not the real-server scale runner."""

import json
import time
from statistics import quantiles

from coalitionkit_acceptance.arena import Arena, accepted
from coalitionkit_runtime import CoalitionHost, SQLiteStore
from coalitionkit_runtime.store import Document
from coalitionkit_surfaces.feed import FeedSession


class FullView:
    def __init__(self, host: CoalitionHost) -> None:
        self.host = host
        self.coalition_id = host.coalition_id

    def view(self, viewer: str) -> Document:
        return self.host.view(viewer)


def measure() -> dict[str, dict[str, float]]:
    arena = Arena.open(SQLiteStore(), deciders=["p0"])
    try:
        for i in range(200):
            arena.enroll(f"p{i}")
        results: dict[str, dict[str, float]] = {}
        for mode, source in [("full_fold", FullView(arena.host)), ("incremental", arena.host)]:
            feeds = [FeedSession(source, f"p{i}", clock=time.monotonic) for i in range(10)]
            for feed in feeds:
                feed.start()
            sends: list[float] = []
            deltas: list[float] = []
            for i in range(20):
                start = time.perf_counter()
                accepted(arena.members["p0"].send("observe", {"source": "chat", "content": str(i)}))
                sends.append(time.perf_counter() - start)
                start = time.perf_counter()
                for feed in feeds:
                    assert feed.changed()
                deltas.append(time.perf_counter() - start)
            results[mode] = {
                "send_p95_s": quantiles(sends, n=20)[18],
                "ten_viewer_update_p95_s": quantiles(deltas, n=20)[18],
            }
        return results
    finally:
        arena.close()


if __name__ == "__main__":
    print(json.dumps(measure()))
