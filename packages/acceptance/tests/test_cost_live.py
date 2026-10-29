# SPDX-License-Identifier: Apache-2.0
"""Acceptance test 8 against live usage: the meter against provider counts and the usage export."""

from __future__ import annotations

import asyncio
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from coalitionkit_acceptance import scorecard
from coalitionkit_acceptance.cost_live import exact_usd, run_live_cost
from coalitionkit_acceptance.ledger import KEY_VAR, StampedMeter, entries, record_run
from coalitionkit_acceptance.live import live_enabled, live_skip_reason
from coalitionkit_acceptance.metrics import SESSION
from coalitionkit_acceptance.privacy_live import CONTRIBUTOR, CONTRIBUTOR_PRICES
from coalitionkit_acceptance.usage_csv import read_export, reconcile
from coalitionkit_models import CostMeter

FIXTURE = Path(__file__).parent / "fixtures" / "usage_export_sample.csv"
DAY1, DAY2 = "2026-01-02", "2026-01-03"
#: The export covers 2 and 3 January; its last day is partial unless a time says otherwise.
THROUGH = datetime(2026, 1, 4, tzinfo=UTC)
NOT_COMPARABLE = "not run: no comparable billing data (export spend is EUR, credit-covered)"


def row(
    day: str, prompt: int, cached: int, completion: int, dedicated: bool = True
) -> dict[str, Any]:
    return {
        "run": "t",
        "dedicated": dedicated,
        "day": day,
        "at": f"{day}T12:00:00.000+00:00",
        "model": CONTRIBUTOR,
        "prompt_tokens": prompt,
        "cached_tokens": cached,
        "completion_tokens": completion,
        "images": 0,
        "audio_ms": 0,
        "cost_micro_usd": 0,
    }


def matching(dedicated: bool = True) -> list[dict[str, Any]]:
    """Ledger rows that add up exactly to the fixture: day 1 has 3 requests, day 2 has 2."""
    return [
        row(DAY1, 400, 100, 200, dedicated),
        row(DAY1, 300, 100, 200, dedicated),
        row(DAY1, 300, 0, 100, dedicated),
        row(DAY2, 600, 0, 250, dedicated),
        row(DAY2, 400, 0, 150, dedicated),
    ]


def one_response() -> CostMeter:
    meter = CostMeter(CONTRIBUTOR_PRICES)
    meter.record(
        "c", "p", CONTRIBUTOR, prompt_tokens=1000, completion_tokens=500, cached_tokens=200
    )
    return meter


def by_status(result: dict[str, Any], status: str) -> list[dict[str, Any]]:
    return [c for c in result["comparisons"] if c["status"] == status]


def test_the_recomputation_from_provider_counts_matches_the_meter() -> None:
    meter = one_response()
    # (800 * 0.10 + 200 * 0.002 + 500 * 0.20) per million tokens
    assert str(exact_usd(meter)) == "0.0001804"
    assert meter.total("c") == 181  # rounded up once per response


def test_the_export_reader_takes_the_real_shape_and_a_bom(tmp_path: Path) -> None:
    plain = read_export(FIXTURE)
    assert plain[DAY1]["input_tokens/cached"] == 200
    assert plain[DAY1]["spend/total"] == 0
    with_bom = tmp_path / "bom.csv"
    with_bom.write_bytes(b"\xef\xbb\xbf" + FIXTURE.read_bytes())
    assert read_export(with_bom) == plain


def test_with_the_dedicated_key_the_ledger_matches_the_export_exactly() -> None:
    result = reconcile(FIXTURE, matching(), key_set=True, until=THROUGH)
    assert result["ran"] and result["mode"] == "exact"
    assert result["differs"] == 0
    assert result["equal"] == 12  # six metrics on each of two days
    assert result["exact_match"] == "ran"
    # Metrics the meter does not record are named as not run, with the reason.
    skipped = by_status(result, "not run")
    assert {c["metric"] for c in skipped} == {
        "images_processed/total",
        "video_frames_processed/total",
        "tool_calls/total",
    }
    assert all("does not record" in c["reason"] for c in skipped)
    # Spend is reported as given in EUR, and the comparison is not run.
    assert result["spend"]["export_spend_as_reported"] == "0"
    assert result["spend"]["export_unit"] == "EUR"
    assert result["spend"]["status"] == NOT_COMPARABLE
    assert result["spend"]["meter_usd_published_rates"] != "0"


def test_a_single_token_of_difference_is_not_an_exact_match() -> None:
    rows = matching()
    rows[0]["completion_tokens"] += 1
    result = reconcile(FIXTURE, rows, key_set=True, until=THROUGH)
    wrong = by_status(result, "differs")
    assert [(c["day"], c["metric"]) for c in wrong] == [(DAY1, "output_tokens")]


def test_without_the_dedicated_key_only_an_upper_bound_is_checked() -> None:
    result = reconcile(FIXTURE, matching(dedicated=False), key_set=False, until=THROUGH)
    assert result["ran"] and result["mode"] == "upper bound"
    assert "equal" not in result and "differs" not in result
    assert result["within_bound"] == 12
    assert result["exceeds_bound"] == 0
    assert result["exact_match"].startswith("not run: no dedicated key")
    # Development calls share the key, so the export may hold more than the meter.
    fewer = matching(dedicated=False)[1:]
    assert reconcile(FIXTURE, fewer, key_set=False, until=THROUGH)["exceeds_bound"] == 0
    # A meter above the export is impossible if both are right: it is flagged.
    more = [*matching(dedicated=False), row(DAY1, 10, 0, 10, False)]
    flagged = by_status(reconcile(FIXTURE, more, key_set=False, until=THROUGH), "exceeds bound")
    assert {c["metric"] for c in flagged} == {"uncached_tokens", "output_tokens", "requests"}


def test_a_day_the_export_lacks_is_not_run_with_the_reason() -> None:
    rows = [*matching(), row("2026-01-01", 10, 0, 10)]
    result = reconcile(FIXTURE, rows, key_set=True, until=THROUGH)
    missing = [c for c in by_status(result, "not run") if c["day"] == "2026-01-01"]
    assert len(missing) == 9
    assert all("no rows for 2026-01-01" in c["reason"] for c in missing[:6])


def test_dedicated_runs_are_needed_for_the_exact_match() -> None:
    result = reconcile(FIXTURE, matching(dedicated=False), key_set=True, until=THROUGH)
    assert result["ran"] is False
    assert "no live usage" in result["reason"]


def test_no_export_file_is_not_run(tmp_path: Path) -> None:
    result = reconcile(tmp_path / "none.csv", matching(), key_set=True)
    assert result["ran"] is False
    assert result["reason"].startswith("not run: no provider usage export")


def test_records_newer_than_the_export_are_not_compared() -> None:
    """A correct export that predates the newest usage must not fail: that usage is not run."""
    result = reconcile(FIXTURE, matching(), key_set=True)  # the export's last day is partial
    assert result["after_window"] == {"records": 2, "status": "not run: after the export window"}
    assert result["differs"] == 0
    assert result["equal"] == 6  # only the first day, whole, is compared
    assert {c["day"] for c in result["comparisons"]} == {DAY1}
    later = [*matching(), row("2026-02-01", 10, 0, 10)]
    assert reconcile(FIXTURE, later, key_set=True, until=THROUGH)["after_window"]["records"] == 1


def test_an_explicit_until_bounds_the_window() -> None:
    noon = datetime(2026, 1, 3, 12, 0, 1, tzinfo=UTC)
    assert reconcile(FIXTURE, matching(), key_set=True, until=noon)["after_window"]["records"] == 0
    early = datetime(2026, 1, 3, 0, 0, tzinfo=UTC)
    assert reconcile(FIXTURE, matching(), key_set=True, until=early)["after_window"]["records"] == 2


def stamped(*moments: datetime) -> StampedMeter:
    """A meter whose clock hands out these moments, one per response."""
    times = iter(moments)
    meter = StampedMeter(CONTRIBUTOR_PRICES, clock=lambda: next(times))
    for index in range(len(moments)):
        meter.record("c", f"p{index}", CONTRIBUTOR, prompt_tokens=100, completion_tokens=50)
    return meter


def test_the_ledger_marks_runs_with_the_dedicated_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "ledger.sqlite3"
    moment = datetime(2026, 1, 2, 12, tzinfo=UTC)
    monkeypatch.delenv(KEY_VAR, raising=False)
    assert record_run("shared", stamped(moment), path=path) == 1
    monkeypatch.setenv(KEY_VAR, "placeholder")
    assert record_run("dedicated", stamped(moment), path=path) == 1
    assert [r["dedicated"] for r in entries(path)] == [False, True]


def test_a_run_spanning_utc_midnight_is_split_by_each_response_time(tmp_path: Path) -> None:
    path = tmp_path / "ledger.sqlite3"
    before = datetime(2026, 1, 2, 23, 59, 59, tzinfo=UTC)
    meter = stamped(before, before + timedelta(seconds=2), before + timedelta(seconds=3))
    record_run("spanning", meter, path=path, dedicated=True)
    assert [r["at"][:10] for r in entries(path)] == [DAY1, DAY2, DAY2]
    # Per UTC day against an export that holds 3 requests and 2 requests on its two days.
    result = reconcile(FIXTURE, entries(path), key_set=True, until=THROUGH)
    requests = {c["day"]: c["meter"] for c in result["comparisons"] if c["metric"] == "requests"}
    assert requests == {DAY1: "1", DAY2: "2"}


APPENDER = """
import sys, time
from pathlib import Path
from coalitionkit_acceptance.ledger import StampedMeter, record_run
from coalitionkit_acceptance.privacy_live import CONTRIBUTOR, CONTRIBUTOR_PRICES
path, name, go = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
while not go.exists():
    time.sleep(0.005)
for index in range(15):
    meter = StampedMeter(CONTRIBUTOR_PRICES)
    meter.record(name, f"p{index}", CONTRIBUTOR, prompt_tokens=10, completion_tokens=5)
    record_run(name, meter, path=path, dedicated=True)
"""


def test_two_processes_appending_at_once_lose_nothing(tmp_path: Path) -> None:
    path, go = tmp_path / "ledger.sqlite3", tmp_path / "go"
    children = [
        subprocess.Popen(
            [sys.executable, "-c", APPENDER, str(path), name, str(go)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        for name in ("first", "second")
    ]
    go.write_text("go", encoding="utf-8")
    outputs = [child.communicate(timeout=120) for child in children]
    assert [child.returncode for child in children] == [0, 0], outputs
    found = entries(path)
    assert len(found) == 30
    assert {r["run"] for r in found} == {"first", "second"}


def eur_export(tmp_path: Path, spend: str, unit: str) -> Path:
    lines = FIXTURE.read_text(encoding="utf-8").splitlines()
    out = [
        line.replace(",spend,total,0,EUR", f",spend,total,{spend},{unit}")
        if ",spend,total," in line
        else line
        for line in lines
    ]
    path = tmp_path / f"export_{unit}.csv"
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return path


def test_a_large_eur_spend_is_reported_as_not_compared(tmp_path: Path) -> None:
    export = eur_export(tmp_path, "9999.99", "EUR")
    result = reconcile(export, matching(), key_set=True, until=THROUGH)
    spend = result["spend"]
    assert spend["status"] == NOT_COMPARABLE
    assert spend["export_unit"] == "EUR"
    assert spend["export_spend_as_reported"] == "19999.98"  # as given, never converted
    # The counts are still compared; the huge spend did not turn them into a pass or a failure.
    assert result["equal"] == 12 and result["differs"] == 0


def test_only_a_usd_spend_is_compared_to_the_cent(tmp_path: Path) -> None:
    export = eur_export(tmp_path, "0", "USD")
    usd = reconcile(export, matching(), key_set=True, until=THROUGH)
    assert usd["spend"]["status"] in {"equal to the cent", "differs"}


def test_the_scorecard_row_survives_every_export_result() -> None:
    """A result that ran has no reason; a missing result has no comparisons: neither may raise."""
    ran = scorecard.Row(8, "Cost")
    scorecard.add_export(ran, {"ran": True, "mode": "exact", "equal": 12, "comparisons": []})
    assert ran.measured["provider_export"]["equal"] == 12
    bound = scorecard.Row(8, "Cost")
    result = reconcile(FIXTURE, matching(dedicated=False), key_set=False, until=THROUGH)
    scorecard.add_export(bound, result)
    assert any("not run: no dedicated key" in p for p in bound.parts)
    absent = scorecard.Row(8, "Cost")
    scorecard.add_export(absent, {"ran": False})
    assert absent.parts == ["provider export: not run"]


def test_without_a_live_run_the_cost_row_reports_no_live_run_and_does_not_crash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("COALITIONKIT_LIVE", raising=False)
    result = asyncio.run(scorecard.run_8())
    assert result.status == "measured"
    assert "provider_export" not in result.measured
    assert any("live: not run" in p and "provider export: not run" in p for p in result.parts)


@pytest.mark.live
async def test_live_meter_matches_the_provider_reported_usage() -> None:
    """Collection only: the meter against the token counts of the responses, re-priced exactly."""
    if not live_enabled():
        pytest.skip(live_skip_reason())
    recorder = await run_live_cost(12)
    SESSION.add(recorder)
    values = recorder.result()["values"]
    reconciliation = values["reconciliation"]
    assert reconciliation["responses"] == 12
    assert reconciliation["meter_micro_usd"] > 0
    # The meter rounds each response up once, so it sits at or just above the exact charge.
    assert 0 <= reconciliation["gap_micro_usd"] < reconciliation["responses"]
    # The provider export is reconciled offline, never in the live run.
    assert "provider_export" not in values
