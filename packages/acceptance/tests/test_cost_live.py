# SPDX-License-Identifier: Apache-2.0
"""Acceptance test 8 against live usage: the meter against the provider-reported counts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from coalitionkit_acceptance.config import USAGE_VAR
from coalitionkit_acceptance.cost_live import compare_export, exact_usd, run_live_cost
from coalitionkit_acceptance.live import live_enabled, live_skip_reason
from coalitionkit_acceptance.metrics import SESSION, Recorder
from coalitionkit_acceptance.privacy_live import CONTRIBUTOR, CONTRIBUTOR_PRICES
from coalitionkit_models import CostMeter


def one_response() -> CostMeter:
    meter = CostMeter(CONTRIBUTOR_PRICES)
    meter.record(
        "c", "p", CONTRIBUTOR, prompt_tokens=1000, completion_tokens=500, cached_tokens=200
    )
    return meter


def test_the_recomputation_from_provider_counts_matches_the_meter() -> None:
    meter = one_response()
    # (800 * 0.10 + 200 * 0.002 + 500 * 0.20) per million tokens
    assert str(exact_usd(meter)) == "0.0001804"
    assert meter.total("c") == 181  # rounded up once per response


def test_a_provider_figure_that_differs_by_a_cent_is_detected(tmp_path: Path) -> None:
    meter = CostMeter(CONTRIBUTOR_PRICES)
    meter.record("c", "p", CONTRIBUTOR, prompt_tokens=60_000_000, completion_tokens=0)
    same = tmp_path / "same.json"
    same.write_text(json.dumps({"billed_usd": "6.00"}), encoding="utf-8")
    off = tmp_path / "off.json"
    off.write_text(json.dumps({"billed_usd": "6.01"}), encoding="utf-8")
    recorder = Recorder("export_probe")
    assert compare_export(meter, recorder, same)["to_the_cent"] is True
    assert compare_export(meter, recorder, off)["to_the_cent"] is False


def test_without_an_export_the_provider_check_is_reported_not_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(USAGE_VAR, raising=False)
    row = compare_export(one_response(), Recorder("none"))
    assert row["ran"] is False
    assert USAGE_VAR in row["reason"]


@pytest.mark.live
async def test_live_spend_is_known_to_the_cent() -> None:
    if not live_enabled():
        pytest.skip(live_skip_reason())
    recorder = await run_live_cost(12)
    SESSION.add(recorder)
    values = recorder.result()["values"]
    row = values["reconciliation"]
    assert row["responses"] == 12
    assert row["meter_micro_usd"] > 0
    assert row["meter_cents"] == row["provider_rates_cents"]
    # The meter rounds each response up once, so it sits at or just above the exact charge.
    assert 0 <= row["gap_micro_usd"] < row["responses"]
    export = values["provider_export"]
    if export["ran"]:
        assert export["to_the_cent"], export
    else:
        # Meta documents no usage endpoint: without the owner's export this part is not run.
        assert USAGE_VAR in export["reason"]
