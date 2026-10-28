# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from pathlib import Path

from coalitionkit_acceptance.metrics import Recorder, Scorecard, percentile


def test_percentile_is_nearest_rank() -> None:
    data = [float(n) for n in range(1, 101)]
    assert percentile(data, 0.5) == 50.0
    assert percentile(data, 0.95) == 95.0
    assert percentile([], 0.95) == 0.0
    assert percentile([3.0], 0.95) == 3.0


def test_scorecard_keeps_measured_values_and_merges_runs(tmp_path: Path) -> None:
    first = Recorder("one")
    first.count("events", 3)
    first.sample("call_s", 0.25)
    card = Scorecard()
    card.add(first)
    path = tmp_path / "out" / "score.json"
    card.write(path)
    second = Scorecard()
    second.add(Recorder("two"))
    second.write(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert set(data["scenarios"]) == {"one", "two"}
    assert data["scenarios"]["one"]["timings"]["call_s"]["p95_s"] == 0.25
    assert "target" not in json.dumps(data)
