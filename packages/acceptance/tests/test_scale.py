# SPDX-License-Identifier: Apache-2.0
"""Acceptance test 5: scale (small at PR time; COALITIONKIT_ACCEPTANCE_FULL=1 runs full size)."""

from __future__ import annotations

from coalitionkit_acceptance.config import scale_size
from coalitionkit_acceptance.metrics import SESSION
from coalitionkit_acceptance.scale import run_scale


def test_no_event_is_lost_at_scale_and_the_meter_adds_up() -> None:
    size = scale_size()
    result, outcomes = run_scale(
        size.big_agents, size.coalitions, size.coalition_agents, size.tasks, size.workers
    )
    SESSION.add(result)
    counts = result["counts"]
    assert counts["lost_events"] == 0
    assert counts["agents_total"] == size.big_agents + size.coalitions * size.coalition_agents
    assert counts["coalitions"] == size.coalitions + 1
    assert counts["coalitions_decided"] == counts["coalitions"]
    assert all(o.lost_events == 0 and o.decided for o in outcomes)
    assert all(o.metered_micro_usd == o.model_cost_micro_usd > 0 for o in outcomes)
    assert result["values"]["cost_micro_usd_metered"] == result["values"]["cost_micro_usd_returned"]
