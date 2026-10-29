# SPDX-License-Identifier: Apache-2.0
"""Acceptance test 8 against live runs: the meter against what the provider can be asked.

Meta documents no usage or billing endpoint (the API reference at
https://dev.meta.ai/docs/api-reference has none; pricing is at
https://dev.meta.ai/docs/pricing-rate-limits). What this module establishes:

* every response carries the provider's own ``usage`` (prompt, cached and completion tokens); the
  meter records are re-priced here from those counts at the published contributor rates with exact
  decimal arithmetic and compared with the meter. This checks the meter arithmetic on provider
  counts; it does not establish what the provider billed.
* a live run only collects each response, stamped with its UTC time, into the ledger. The usage
  CSV the owner exports from the dashboard is reconciled offline with the ``reconcile`` module
  (see its docstring), per UTC day and metric, over the window the export covers. Spend is not
  compared: the export gives EUR, credit-covered.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

from coalitionkit_models import CostMeter
from coalitionkit_models.gateway import ChatMessage

from .config import USAGE_VAR
from .ledger import record_run
from .live import CONTRIBUTOR, close_kit, live_kit
from .metrics import Recorder
from .usage_csv import reconcile as reconcile_export

MICRO = Decimal(1_000_000)
CENT = Decimal("0.01")
#: dev.meta.ai pricing, contributor tier, USD per 1M tokens (measured 2026-10-28).
RATES = {"input": Decimal("0.10"), "cached_input": Decimal("0.002"), "output": Decimal("0.20")}


def exact_usd(meter: CostMeter, coalitions: set[str] | None = None) -> Decimal:
    """What the provider's published rates charge for the responses the meter recorded."""
    total = Decimal(0)
    for record in meter.records:
        if coalitions is not None and record.coalition_id not in coalitions:
            continue
        cached = min(record.cached_tokens, record.prompt_tokens)
        total += (
            (record.prompt_tokens - cached) * RATES["input"]
            + cached * RATES["cached_input"]
            + record.completion_tokens * RATES["output"]
        ) / MICRO
    return total


def cents(usd: Decimal) -> Decimal:
    return usd.quantize(CENT, rounding=ROUND_HALF_UP)


def reconcile(meter: CostMeter, recorder: Recorder, label: str = "") -> dict[str, Any]:
    metered = sum(r.cost_micro_usd for r in meter.records)
    exact = exact_usd(meter)
    gap = int(Decimal(metered) - exact * MICRO)
    row: dict[str, Any] = {
        "responses": len(meter.records),
        "prompt_tokens": sum(r.prompt_tokens for r in meter.records),
        "cached_tokens": sum(r.cached_tokens for r in meter.records),
        "completion_tokens": sum(r.completion_tokens for r in meter.records),
        "meter_micro_usd": metered,
        "provider_rates_exact_usd": str(exact),
        "gap_micro_usd": gap,
        "meter_cents": str(cents(Decimal(metered) / MICRO)),
        "provider_rates_cents": str(cents(exact)),
    }
    recorder.value(f"reconciliation{label}", row)
    return row


def export_path() -> Path | None:
    value = os.environ.get(USAGE_VAR, "").strip()
    return Path(value) if value else None


def export_comparison(recorder: Recorder, path: Path | None = None) -> dict[str, Any]:
    """Every recorded live run against the provider export; or why that did not run."""
    row = reconcile_export(path or export_path())
    recorder.value("provider_export", row)
    return row


async def run_live_cost(calls: int = 12) -> Recorder:
    """A few live responses over three Coalitions, then the reconciliation."""
    recorder = Recorder("cost_live")
    kit = live_kit()
    started = datetime.now(UTC)
    try:
        for index in range(calls):
            message: ChatMessage = {
                "role": "user",
                "content": f"Reply with exactly the word ok. Number {index}.",
            }
            await kit.agents.complete(
                "hosted_agent",
                [message],
                coalition_id=f"cost-live-{index % 3}",
                participant=f"a{index}",
                reasoning_effort="minimal",
            )
    finally:
        await close_kit(kit)
    recorder.value("window", [started.isoformat(), datetime.now(UTC).isoformat()])
    recorder.value("model", CONTRIBUTOR)
    row = reconcile(kit.meter, recorder)
    record_run("cost_live", kit.meter)  # collection only; reconciliation is offline
    recorder.count("responses", row["responses"])
    recorder.value("cost_micro_usd_metered", row["meter_micro_usd"])
    recorder.value("live_cost_micro_usd", row["meter_micro_usd"])
    return recorder
