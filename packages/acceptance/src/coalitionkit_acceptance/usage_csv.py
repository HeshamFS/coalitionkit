# SPDX-License-Identifier: Apache-2.0
"""Reconcile the live ledger with Meta usage export (the CSV the dashboard downloads).

Shape: header ``date,metric,series,value,unit``, one row per day per metric/series, totals over the
keys and models the dashboard was filtered to. Metrics: ``spend/total`` (EUR), ``input_tokens``
(``cached``, ``uncached``, ``batch_cached``, ``batch_uncached``), ``output_tokens`` (``output``,
``batch_output``), ``requests/total``, ``images/total``, ``images_processed/total``,
``video_frames_processed/total``, ``audio_transcription/total`` (seconds), ``tool_calls/total``.
Usage can take up to an hour to appear in the export.

The export carries no key column. With the dedicated acceptance key
(``COALITIONKIT_META_ACCEPTANCE_KEY``) set, the export is taken to be filtered to it and the match
is exact. Without it the export is all-key and only an upper bound is checked (never presented as a
match); the exact match is then reported as not run. Spend is not compared: the export EUR spend
is reported as given (0 while the account credit covers it), next to the USD the published price
table gives. No currency is ever converted.
"""

from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path
from typing import Any

from .ledger import KEY_VAR, dedicated_key_set, entries

RATES = {"input": Decimal("0.10"), "cached_input": Decimal("0.002"), "output": Decimal("0.20")}
MILLION = Decimal(1_000_000)
NO_KEY = f"no dedicated key (set {KEY_VAR}; the export is only comparable when filtered to it)"

#: (name, export series that add up to it)
COMPARED: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("cached_tokens", ("input_tokens/cached", "input_tokens/batch_cached")),
    ("uncached_tokens", ("input_tokens/uncached", "input_tokens/batch_uncached")),
    ("output_tokens", ("output_tokens/output", "output_tokens/batch_output")),
    ("requests", ("requests/total",)),
    ("images", ("images/total",)),
    ("audio_seconds", ("audio_transcription/total",)),
)
NOT_RECORDED = ("images_processed/total", "video_frames_processed/total", "tool_calls/total")


def read_export(path: Path) -> dict[str, dict[str, Decimal]]:
    """``{day: {"metric/series": value}}`` from the CSV (a leading BOM is tolerated)."""
    days: dict[str, dict[str, Decimal]] = {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            key = f"{row['metric']}/{row['series']}"
            days.setdefault(row["date"], {})[key] = Decimal(row["value"])
    return days


def meter_day(rows: list[dict[str, Any]]) -> dict[str, Decimal]:
    return {
        "cached_tokens": Decimal(sum(r["cached_tokens"] for r in rows)),
        "uncached_tokens": Decimal(sum(r["prompt_tokens"] - r["cached_tokens"] for r in rows)),
        "output_tokens": Decimal(sum(r["completion_tokens"] for r in rows)),
        "requests": Decimal(len(rows)),
        "images": Decimal(sum(r["images"] for r in rows)),
        "audio_seconds": Decimal(sum(r["audio_ms"] for r in rows)) / 1000,
    }


def meter_usd(rows: list[dict[str, Any]]) -> Decimal:
    """USD for the ledger at the published rates, exact (no rounding)."""
    total = Decimal(0)
    for r in rows:
        cached = min(r["cached_tokens"], r["prompt_tokens"])
        total += (
            (r["prompt_tokens"] - cached) * RATES["input"]
            + cached * RATES["cached_input"]
            + r["completion_tokens"] * RATES["output"]
        ) / MILLION
    return total


def not_run(day: str, metric: str, reason: str) -> dict[str, Any]:
    return {"day": day, "metric": metric, "status": "not run", "reason": reason}


def compared(
    day: str, metric: str, meter: Decimal, export: Decimal, *, exact: bool
) -> dict[str, Any]:
    if exact:
        status = "equal" if meter == export else "differs"
    else:  # an all-key export also holds development calls: the meter can only be at most it
        status = "within bound" if meter <= export else "exceeds bound"
    return {
        "day": day,
        "metric": metric,
        "status": status,
        "meter": str(meter),
        "export": str(export),
    }


def compare_day(
    day: str, rows: list[dict[str, Any]], theirs: dict[str, Decimal] | None, *, exact: bool
) -> list[dict[str, Any]]:
    mine = meter_day(rows)
    found: list[dict[str, Any]] = []
    for name, series in COMPARED:
        if theirs is None:
            why = f"the export has no rows for {day} (usage can take an hour to appear)"
            found.append(not_run(day, name, why))
            continue
        missing = [s for s in series if s not in theirs]
        if missing:
            found.append(not_run(day, name, "the export lacks " + ", ".join(missing)))
        else:
            total = sum((theirs[s] for s in series), Decimal(0))
            found.append(compared(day, name, mine[name], total, exact=exact))
    for metric in NOT_RECORDED:
        found.append(not_run(day, metric, f"the cost meter does not record {metric.split('/')[0]}"))
    return found


def reconcile(
    export: Path | None,
    ledger_rows: list[dict[str, Any]] | None = None,
    *,
    key_set: bool | None = None,
) -> dict[str, Any]:
    """Compare the merged ledger with the export, per day and per metric.

    With the dedicated key the export is filtered to it and the dedicated records must match it
    exactly. Without it the export holds every call of the account, so the check is only an upper
    bound (meter at most export) and the exact match is reported as not run.
    """
    every = entries() if ledger_rows is None else ledger_rows
    exact = dedicated_key_set() if key_set is None else key_set
    rows = [r for r in every if r.get("dedicated")] if exact else every
    if export is None or not export.is_file():
        return {"ran": False, "reason": "not run: no provider usage export file", "comparisons": []}
    if not rows:
        return {"ran": False, "reason": "not run: no live usage in the ledger", "comparisons": []}
    exported = read_export(export)
    days = sorted({r["day"] for r in rows})
    comparisons: list[dict[str, Any]] = []
    for day in days:
        mine = [r for r in rows if r["day"] == day]
        comparisons += compare_day(day, mine, exported.get(day), exact=exact)
    made = [c for c in comparisons if c["status"] != "not run"]
    good, bad = ("equal", "differs") if exact else ("within bound", "exceeds bound")
    spend = sum((exported.get(d, {}).get("spend/total", Decimal(0)) for d in days), Decimal(0))
    return {
        "ran": bool(made),
        "mode": "exact" if exact else "upper bound",
        "reason": "" if made else "not run: every comparison was not run; see the comparisons",
        "exact_match": "ran" if exact else "not run: " + NO_KEY,
        good.replace(" ", "_"): sum(1 for c in made if c["status"] == good),
        bad.replace(" ", "_"): sum(1 for c in made if c["status"] == bad),
        "not_run": sum(1 for c in comparisons if c["status"] == "not run"),
        "comparisons": comparisons,
        "spend": {
            "meter_usd_published_rates": str(meter_usd(rows)),
            "export_spend_as_reported": str(spend),
            "export_unit": "EUR",
            "note": "not converted or compared; 0 in the export means the account credit covers it",
        },
    }
