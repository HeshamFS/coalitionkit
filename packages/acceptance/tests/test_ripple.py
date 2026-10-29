# SPDX-License-Identifier: Apache-2.0
"""Acceptance test 4: a change in the middle of a 20-task plan."""

from __future__ import annotations

from coalitionkit_acceptance.metrics import SESSION
from coalitionkit_acceptance.ripple import run_ripple


def test_only_affected_tasks_are_renegotiated() -> None:
    result = run_ripple()
    SESSION.add(result.metrics)
    assert len(result.affected) == 5
    assert result.replanned == result.affected
    assert result.proposed_after == result.affected
    assert result.renegotiated == result.affected
    assert result.unchanged_assignments
    assert set(result.final_status.values()) == {"decided"}
    assert result.viewers_lost == 0
    timings = result.metrics["timings"]
    assert timings["projection_s"]["n"] == 4
    assert timings["bus_delivery_s"]["n"] == 4
    assert timings["projection_s"]["p95_s"] > 0
