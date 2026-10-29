# SPDX-License-Identifier: Apache-2.0
"""Acceptance test 8: the cost meter against recorded provider usage, to the cent."""

from __future__ import annotations

import json
from pathlib import Path

from coalitionkit_acceptance.config import usage_file
from coalitionkit_acceptance.cost import default_usage_file, rates_match_price_table, run_cost
from coalitionkit_acceptance.metrics import SESSION


def test_meter_equals_provider_usage_to_the_cent() -> None:
    path = usage_file(default_usage_file())
    recorder, report = run_cost(path)
    SESSION.add(recorder)
    assert recorder.counter("calls") == recorder.counter("calls_served") > 0
    for name, row in report.items():
        assert row["meter_cents"] == row["provider_billed_cents"], name
    assert recorder.result()["values"]["cents_mismatches"] == 0
    # The meter rounds each response up once, so it sits at or just above the exact charge.
    gaps = [row["gap_micro_usd"] for row in report.values()]
    assert all(0 <= gap < recorder.counter("calls") for gap in gaps)


def test_recorded_rates_are_the_bundled_price_table() -> None:
    usage = json.loads(default_usage_file().read_text(encoding="utf-8"))
    assert rates_match_price_table(usage) == []


def test_a_wrong_charge_is_detected(tmp_path: Path) -> None:
    usage = json.loads(default_usage_file().read_text(encoding="utf-8"))
    name = sorted(usage["billed_cents"])[0]
    usage["billed_cents"][name] = "9.99"
    altered = tmp_path / "usage.json"
    altered.write_text(json.dumps(usage), encoding="utf-8")
    recorder, _ = run_cost(altered)
    assert recorder.result()["values"]["cents_mismatches"] == 1
