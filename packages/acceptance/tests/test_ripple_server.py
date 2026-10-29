# SPDX-License-Identifier: Apache-2.0
"""Acceptance test 4 over the real server, with SSE viewers on /v1/feed."""

from __future__ import annotations

from pathlib import Path

from coalitionkit_acceptance.metrics import SESSION
from coalitionkit_acceptance.ripple_server import run_ripple_server
from coalitionkit_acceptance.sse import FeedViewer


async def test_only_the_ripple_is_renegotiated_and_surfaces_follow_within_two_seconds(
    tmp_path: Path,
) -> None:
    result = await run_ripple_server(tmp_path)
    SESSION.add(result.metrics)
    assert len(result.affected) == 5
    assert result.replanned == result.affected
    assert result.renegotiated == result.affected
    assert result.proposed_after == result.affected
    assert result.unchanged_assignments
    assert result.decided
    # Nothing lost or invented at any of the twelve viewers.
    assert result.lost_events == 0
    assert result.extra_events == 0
    assert result.viewers == 12
    # Viewers outside the ripple get no delta at all, so no news of re-negotiated tasks.
    assert len(result.unaffected) >= 4
    assert result.unaffected_deltas == 0
    assert result.unaffected_saw_new_events == 0
    # Every affected viewer's surface moved, and quickly.
    timings = result.metrics["timings"]
    assert timings["change_to_surface_s"]["n"] == len(result.audience)
    assert timings["change_to_surface_s"]["p95_s"] < 2.0
    assert timings["accept_to_delta_s"]["n"] == result.samples
    assert result.samples >= 3 * len(result.audience)
    assert timings["accept_to_delta_s"]["p95_s"] < 2.0


def test_a_viewer_that_missed_a_delta_is_counted_as_lost() -> None:
    viewer = FeedViewer("p1", "http://127.0.0.1:1", "token")
    viewer.take({"type": "STATE_SNAPSHOT", "snapshot": {"events": {"a": {}}}})
    viewer.take({"type": "STATE_DELTA", "delta": [{"op": "add", "path": "/events/b", "value": {}}]})
    assert viewer.event_ids() == {"a", "b"}
    truth = {"a", "b", "c"}
    assert len(truth - viewer.event_ids()) == 1
