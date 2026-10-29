# SPDX-License-Identifier: Apache-2.0
"""Acceptance test 5 over the real server (small at PR time; COALITIONKIT_ACCEPTANCE_FULL=1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from coalitionkit_acceptance.config import scale_size
from coalitionkit_acceptance.cost_live import reconcile
from coalitionkit_acceptance.ledger import record_run
from coalitionkit_acceptance.live import close_kit, live_enabled, live_kit, live_skip_reason
from coalitionkit_acceptance.metrics import SESSION, Recorder
from coalitionkit_acceptance.scale_server import run_scale_server

LIVE_AGENTS = 20


async def test_no_event_is_lost_over_the_real_server_and_cost_is_recorded(tmp_path: Path) -> None:
    size = scale_size()
    result = await run_scale_server(
        tmp_path,
        agents=size.big_agents,
        coalitions=size.coalitions,
        coalition_agents=size.coalition_agents,
        tasks=size.tasks,
        big_viewers=10,
        small_viewers=2,
        concurrency=size.workers,
    )
    SESSION.add(result)
    counts = result["counts"]
    assert counts["lost_events"] == 0
    assert counts["viewer_lost_events"] == 0
    assert counts["agents_total"] == size.big_agents + size.coalitions * size.coalition_agents
    assert counts["coalitions"] == size.coalitions + 1
    assert counts["coalitions_decided"] == counts["coalitions"]
    assert counts["viewers"] == 10 + 2 * size.coalitions
    assert result["timings"]["send_s"]["n"] > 0
    assert result["timings"]["send_s"]["p95_s"] > 0
    # Acceptance (the server's stamp) to the delta at the sampled viewers; never negative.
    assert result["timings"]["accept_to_delta_s"]["n"] > 0
    assert result["timings"]["accept_to_delta_s"]["min_s"] >= 0
    assert counts.get("negative_latencies", 0) == 0
    # Each agent asks the model once per offer, and the Steward audits each plan.
    assert counts["model_calls"] >= counts["agents_total"] * 2
    assert result["values"]["cost_micro_usd_metered"] > 0


@pytest.mark.live
async def test_twenty_live_model_agents_among_scripted_ones(tmp_path: Path) -> None:
    if not live_enabled():
        pytest.skip(live_skip_reason())
    size = scale_size()
    kit = live_kit()
    try:
        result = await run_scale_server(
            tmp_path,
            agents=size.big_agents,
            coalitions=0,
            coalition_agents=size.coalition_agents,
            tasks=size.tasks,
            big_viewers=10,
            small_viewers=0,
            concurrency=size.workers,
            live=LIVE_AGENTS,
            kit=kit,
        )
    finally:
        await close_kit(kit)
    recorder = Recorder("scale_live")
    row = reconcile(kit.meter, recorder)
    recorder.value("scale", result)
    record_run("scale_live", kit.meter)
    recorder.value("live_cost_micro_usd", row["meter_micro_usd"])
    recorder.value("cost_micro_usd_metered", row["meter_micro_usd"])
    latencies = [x for t in kit.transports for x in t.latencies]
    for seconds in latencies:
        recorder.sample("live_call_s", seconds)
    SESSION.add(recorder)
    counts = result["counts"]
    assert counts["lost_events"] == 0
    assert counts["viewer_lost_events"] == 0
    assert counts["coalitions_decided"] == 1
    # Twenty agents made two live calls each, and the Steward audited the plan.
    assert len(latencies) >= LIVE_AGENTS * 2 + 1
    assert row["meter_micro_usd"] > 0
    assert row["responses"] >= len(latencies)
