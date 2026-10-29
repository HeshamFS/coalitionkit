# SPDX-License-Identifier: Apache-2.0
"""One scenario over the real A2A edge on a local port."""

from __future__ import annotations

from coalitionkit_acceptance.metrics import SESSION
from coalitionkit_acceptance.wire import run_wire


async def test_members_reach_the_host_over_a2a_and_nothing_is_lost() -> None:
    result = await run_wire()
    SESSION.add(result.metrics)
    assert result.plan_decided
    assert result.metrics["counts"]["lost_events"] == 0
    assert result.acknowledged == 11
    assert result.refused_codes == ["stage_mismatch"]
