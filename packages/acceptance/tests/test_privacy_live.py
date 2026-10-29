# SPDX-License-Identifier: Apache-2.0
"""Live variant of acceptance test 2: a model plays the adversary. Runs only with a key."""

from __future__ import annotations

from collections import Counter

import pytest

from coalitionkit_acceptance.adversaries import Attacker
from coalitionkit_acceptance.metrics import SESSION, Recorder, percentile
from coalitionkit_acceptance.privacy import PrivacyResult, record, run_privacy
from coalitionkit_acceptance.privacy_live import (
    LiveDriver,
    LiveReport,
    action_mix,
    check_live_report,
    guessed_canaries,
    live_enabled,
    live_skip_reason,
    new_gateway,
    new_meter,
)
from coalitionkit_acceptance.privacy_world import PrivacyWorld

RUNS = 5


async def idle(_attacker: Attacker) -> None:
    return None


@pytest.mark.live
async def test_live_model_adversaries_find_no_canary() -> None:
    if not live_enabled():
        pytest.skip(live_skip_reason())
    recorder = Recorder("privacy_live")
    meter = new_meter()
    gateway, transport = new_gateway(meter)
    outcomes: list[PrivacyResult] = []
    reports: list[LiveReport] = []
    try:
        for seed in range(RUNS):
            report = LiveReport()
            driver = LiveDriver(gateway, f"run-{seed}", report)
            first = len(transport.calls)

            async def finish(
                world: PrivacyWorld, start: int = first, r: LiveReport = report
            ) -> None:
                for messages in transport.calls[start:]:
                    world.record("prompt", "p1", "live adversary", messages, owner="p1")
                world.record("adversary_guess", "p1", "final guesses", r.guesses)
                recorder.count(
                    "guesses_naming_a_foreign_canary",
                    len(guessed_canaries(world.registry, world.ledger, r.guesses, "p1")),
                )

            drivers = {"p1": driver, "p2": idle, "p3": idle, "p4": idle}
            outcome = await run_privacy(seed, drivers=drivers, after_attacks=finish)
            record(recorder, outcome)
            outcomes.append(outcome)
            reports.append(report)
    finally:
        await transport.aclose()
    latencies = transport.latencies
    recorder.count("model_calls", len(transport.calls))
    records = meter.records
    recorder.count("prompt_tokens", sum(r.prompt_tokens for r in records))
    recorder.count("completion_tokens", sum(r.completion_tokens for r in records))
    recorder.count("cost_micro_usd", sum(r.cost_micro_usd for r in records))
    recorder.count("adversary_turns", sum(r.turns for r in reports))
    recorder.count("unparseable_replies", sum(r.parse_failures for r in reports))
    recorder.count("empty_replies", sum(r.empty_replies for r in reports))
    recorder.value("model", "muse-spark-1.3-contributor")
    recorder.value("latency_p50_s", round(percentile(latencies, 0.5), 3))
    recorder.value("latency_p95_s", round(percentile(latencies, 0.95), 3))
    recorder.count("invalid_actions", sum(r.invalid for r in reports))
    mix: Counter[str] = Counter()
    for r in reports:
        mix.update(r.actions)
    attacks: Counter[str] = Counter()
    for r in reports:
        attacks.update(r.attacks)
    recorder.value("attack_mix", dict(sorted(attacks.items())))
    recorder.value("action_mix", dict(sorted(mix.items())))
    recorder.value("action_mix_per_run", [action_mix(r) for r in reports])
    SESSION.add(recorder)
    for index, r in enumerate(reports):
        try:
            check_live_report(r)
        except AssertionError as exc:
            raise AssertionError(f"live run {index} was not adversarial: {exc}") from exc
    assert recorder.counter("model_calls") > 0
    assert recorder.counter("canaries_found_outside_vault") == 0, [
        leak.describe() for o in outcomes for leak in o.leaks
    ]
