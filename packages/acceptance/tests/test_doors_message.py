# SPDX-License-Identifier: Apache-2.0
"""Acceptance test 3, message door: scope per member, no decision from a reply, delivery time."""

from __future__ import annotations

from pathlib import Path

import pytest

from coalitionkit_acceptance.doors_message import MEMBERS, run_live_prompts, run_message_door
from coalitionkit_acceptance.metrics import SESSION, Recorder, Scorecard, percentile
from coalitionkit_acceptance.privacy_live import (
    live_enabled,
    live_skip_reason,
    new_gateway,
    new_meter,
)

#: Gitignored: packages/acceptance/scorecard-*.json
SCORECARD = Path(__file__).resolve().parents[1] / "scorecard-message.json"


def test_each_member_gets_only_its_own_scope_and_a_reply_signs_nothing() -> None:
    result = run_message_door()
    SESSION.add(result.recorder)
    card = Scorecard()
    card.add(result.recorder)
    card.write(SCORECARD)
    assert result.leaks == []
    assert result.seen == result.expected
    assert all(result.expected[name] > 0 for name in MEMBERS)
    assert result.decisions_from_replies == 0
    assert result.tickets == 1
    assert result.max_message_length <= 1000
    timing = result.recorder.result()["timings"]["delivery_s"]
    assert timing["n"] > 0
    assert 0 < timing["p50_s"] <= timing["p95_s"] <= timing["max_s"]


@pytest.mark.live
async def test_live_model_member_replies_with_an_option_number() -> None:
    if not live_enabled():
        pytest.skip(live_skip_reason())
    recorder = Recorder("doors_message_live")
    meter = new_meter()
    gateway, transport = new_gateway(meter)
    try:
        result = await run_live_prompts(gateway, recorder)
    finally:
        await transport.aclose()
    records = meter.records
    recorder.count("prompt_tokens", sum(r.prompt_tokens for r in records))
    recorder.count("completion_tokens", sum(r.completion_tokens for r in records))
    recorder.count("cost_micro_usd", sum(r.cost_micro_usd for r in records))
    recorder.value("model", "muse-spark-1.3-contributor")
    recorder.value("replies", result.replies)
    recorder.value("latency_p50_s", round(percentile(transport.latencies, 0.5), 3))
    recorder.value("latency_p95_s", round(percentile(transport.latencies, 0.95), 3))
    SESSION.add(recorder)
    card = Scorecard()
    card.add(recorder)
    card.write(SCORECARD)
    assert result.prompts > 0
