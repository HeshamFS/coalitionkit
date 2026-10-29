# SPDX-License-Identifier: Apache-2.0
"""The ledger of live acceptance usage: every live run's meter records, with the UTC day.

The provider export is per day and per key, so the check needs every live run of a window merged
into one meter. Each live run appends its records here when it ends, marked ``dedicated`` when the
run used the dedicated acceptance key (``COALITIONKIT_META_ACCEPTANCE_KEY``). Only dedicated
records can be matched exactly with an export filtered to that key; all records are at most the
totals of an all-key export (development calls share the key). Delete the file to start a new
window.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from coalitionkit_models import CostMeter

LEDGER_VAR = "COALITIONKIT_ACCEPTANCE_LEDGER"
KEY_VAR = "COALITIONKIT_META_ACCEPTANCE_KEY"
#: Matches the existing .gitignore line for packages/acceptance/scorecard-*.json.
DEFAULT = Path(__file__).resolve().parents[2] / "scorecard-ledger.json"


def dedicated_key_set() -> bool:
    return bool(os.environ.get(KEY_VAR, "").strip())


def ledger_path() -> Path:
    value = os.environ.get(LEDGER_VAR, "").strip()
    return Path(value) if value else DEFAULT


def entries(path: Path | None = None) -> list[dict[str, Any]]:
    chosen = path or ledger_path()
    if not chosen.is_file():
        return []
    return list(json.loads(chosen.read_text(encoding="utf-8")))


def record_run(
    run: str,
    meter: CostMeter,
    *,
    path: Path | None = None,
    day: str | None = None,
    dedicated: bool | None = None,
) -> int:
    """Append the meter records; returns how many."""
    marked = dedicated_key_set() if dedicated is None else dedicated
    chosen = path or ledger_path()
    stamp = day or datetime.now(UTC).strftime("%Y-%m-%d")
    added = [
        {
            "run": run,
            "dedicated": marked,
            "day": stamp,
            "model": r.model,
            "prompt_tokens": r.prompt_tokens,
            "cached_tokens": r.cached_tokens,
            "completion_tokens": r.completion_tokens,
            "images": r.images,
            "audio_ms": r.audio_ms,
            "cost_micro_usd": r.cost_micro_usd,
        }
        for r in meter.records
    ]
    chosen.write_text(json.dumps([*entries(chosen), *added], indent=1) + "\n", encoding="utf-8")
    return len(added)
