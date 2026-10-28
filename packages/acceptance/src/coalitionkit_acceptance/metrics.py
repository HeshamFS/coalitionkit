# SPDX-License-Identifier: Apache-2.0
"""A small recorder: counts, timing samples and wall time, and a JSON scorecard of measurements."""

from __future__ import annotations

import json
import math
import time
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from typing import Any


def percentile(samples: Sequence[float], fraction: float) -> float:
    """Nearest-rank percentile (``fraction`` in 0..1); 0.0 for no samples."""
    if not samples:
        return 0.0
    ordered = sorted(samples)
    rank = max(1, math.ceil(fraction * len(ordered)))
    return ordered[min(rank, len(ordered)) - 1]


class Recorder:
    """Thread-safe: counters, sample series (seconds) and values for one scenario run."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._lock = Lock()
        self._counts: dict[str, int] = {}
        self._series: dict[str, list[float]] = {}
        self._values: dict[str, Any] = {}
        self._started = time.perf_counter()

    def count(self, key: str, amount: int = 1) -> None:
        with self._lock:
            self._counts[key] = self._counts.get(key, 0) + amount

    def sample(self, key: str, seconds: float) -> None:
        with self._lock:
            self._series.setdefault(key, []).append(seconds)

    def value(self, key: str, value: Any) -> None:
        with self._lock:
            self._values[key] = value

    @contextmanager
    def timed(self, key: str) -> Generator[None]:
        start = time.perf_counter()
        try:
            yield
        finally:
            self.sample(key, time.perf_counter() - start)

    def counter(self, key: str) -> int:
        return self._counts.get(key, 0)

    def series(self, key: str) -> list[float]:
        return list(self._series.get(key, []))

    def result(self) -> dict[str, Any]:
        """Measured values only. Seconds are rounded to microseconds."""
        with self._lock:
            summary = {
                key: {
                    "n": len(data),
                    "p50_s": round(percentile(data, 0.5), 6),
                    "p95_s": round(percentile(data, 0.95), 6),
                    "max_s": round(max(data), 6),
                }
                for key, data in sorted(self._series.items())
                if data
            }
            return {
                "scenario": self.name,
                "wall_s": round(time.perf_counter() - self._started, 3),
                "counts": dict(sorted(self._counts.items())),
                "timings": summary,
                "values": dict(sorted(self._values.items())),
            }


class Scorecard:
    """Collects scenario results and writes them as one JSON file."""

    def __init__(self) -> None:
        self.runs: list[dict[str, Any]] = []

    def add(self, recorder: Recorder | dict[str, Any]) -> dict[str, Any]:
        result = recorder if isinstance(recorder, dict) else recorder.result()
        self.runs.append(result)
        return result

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        merged: dict[str, Any] = {}
        if path.exists():
            try:
                merged = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                merged = {}
        scenarios: dict[str, Any] = dict(merged.get("scenarios", {}))
        for run in self.runs:
            scenarios[run["scenario"]] = run
        path.write_text(
            json.dumps({"scenarios": scenarios}, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


#: Every scenario a test session ran; written once at the end when a scorecard path is set.
SESSION = Scorecard()
