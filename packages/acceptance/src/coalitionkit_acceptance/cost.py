# SPDX-License-Identifier: Apache-2.0
"""Acceptance test 8: the cost meter against the provider's own usage records, to the cent.

A usage file lists every call the provider billed (role, model, token counts) and what the
provider charged per Coalition in whole cents, computed from its own published rates. The
scenario replays the calls through the real gateway and meter and compares. PR runs use the
recorded fixture; set ``COALITIONKIT_ACCEPTANCE_USAGE_FILE`` to compare a live export.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping, Sequence
from decimal import ROUND_HALF_UP, Decimal
from importlib import resources
from pathlib import Path
from typing import Any

from coalitionkit_models import CostMeter, ModelGateway, Settings, load_price_table
from coalitionkit_models.gateway import ChatMessage, RawCompletion, Usage
from coalitionkit_models.settings import ROLES, Role, Route

from .metrics import Recorder

MICRO = Decimal(1_000_000)
CENT = Decimal("0.01")


def default_usage_file() -> Path:
    return Path(str(resources.files("coalitionkit_acceptance").joinpath("fixtures/usage.json")))


class ReplayTransport:
    """Answers each call with the next recorded usage, and checks the model the route chose."""

    def __init__(self, calls: Sequence[Mapping[str, Any]]) -> None:
        self._calls = list(calls)
        self.served = 0

    async def create(
        self, route: Route, messages: Sequence[ChatMessage], opts: Mapping[str, Any]
    ) -> RawCompletion:
        call = self._calls[self.served]
        self.served += 1
        if route.model != call["model"]:
            raise AssertionError(f"role {route.role} routes to {route.model}, not {call['model']}")
        return RawCompletion(
            "recorded",
            Usage(call["prompt_tokens"], call["completion_tokens"], call["cached_tokens"]),
        )


def provider_usd(rates: Mapping[str, Any], call: Mapping[str, Any]) -> Decimal:
    """What the provider charges for one call, exactly, from its USD-per-million rates."""
    rate = rates[call["model"]]
    cached = min(call["cached_tokens"], call["prompt_tokens"])
    scaled = (
        (call["prompt_tokens"] - cached) * Decimal(rate["input"])
        + cached * Decimal(rate["cached_input"])
        + call["completion_tokens"] * Decimal(rate["output"])
    )
    return scaled / MICRO


def cents(usd: Decimal) -> Decimal:
    return usd.quantize(CENT, rounding=ROUND_HALF_UP)


def run_cost(path: Path | None = None) -> tuple[Recorder, dict[str, dict[str, Any]]]:
    """Replay a usage file; return the recorder and a per-Coalition comparison."""
    usage = json.loads((path or default_usage_file()).read_text(encoding="utf-8"))
    calls: list[dict[str, Any]] = usage["calls"]
    recorder = Recorder("cost")
    table = load_price_table()
    meter = CostMeter(table)
    limits = dict.fromkeys(ROLES, 10_000_000)
    settings = Settings(  # the recorded usage ran the Steward on its Baseten host
        _env_file=None,  # pyright: ignore[reportCallIssue]
        rate_limit_per_minute=limits,
        steward_provider="baseten",
    )
    transport = ReplayTransport(calls)
    gateway = ModelGateway(settings, transport=transport, meter=meter)

    async def replay() -> None:
        for call in calls:
            role: Role = call["role"]
            message: ChatMessage = {"role": "user", "content": "recorded call"}
            await gateway.complete(
                role, [message], coalition_id=call["coalition"], participant=call["participant"]
            )

    asyncio.run(replay())
    exact: dict[str, Decimal] = {}
    for call in calls:
        exact[call["coalition"]] = exact.get(call["coalition"], Decimal(0)) + provider_usd(
            usage["rates_usd_per_mtok"], call
        )
    report: dict[str, dict[str, Any]] = {}
    for coalition, billed in sorted(usage["billed_cents"].items()):
        metered = Decimal(meter.total(coalition)) / MICRO
        report[coalition] = {
            "meter_micro_usd": meter.total(coalition),
            "provider_exact_usd": str(exact[coalition]),
            "meter_cents": str(cents(metered)),
            "provider_billed_cents": str(billed),
            "provider_cents_from_rates": str(cents(exact[coalition])),
            "gap_micro_usd": int((metered - exact[coalition]) * MICRO),
        }
    recorder.count("calls", len(calls))
    recorder.count("calls_served", transport.served)
    recorder.count("coalitions", len(report))
    recorder.value("meter_total_micro_usd", sum(meter.total(c) for c in report))
    recorder.value("max_gap_micro_usd", max(abs(r["gap_micro_usd"]) for r in report.values()))
    recorder.value(
        "cents_mismatches",
        sum(1 for r in report.values() if r["meter_cents"] != r["provider_billed_cents"]),
    )
    recorder.value("per_coalition", report)
    return recorder, report


def rates_match_price_table(usage: Mapping[str, Any]) -> list[str]:
    """Models whose recorded provider rate differs from the bundled price table."""
    table = load_price_table()
    out: list[str] = []
    for model, rate in usage["rates_usd_per_mtok"].items():
        price = table.price(model)
        theirs = tuple(Decimal(rate[k]) * MICRO for k in ("input", "output", "cached_input"))
        ours = (Decimal(price.input), Decimal(price.output), Decimal(price.cached_input))
        if theirs != ours:
            out.append(model)
    return out
