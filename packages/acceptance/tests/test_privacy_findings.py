# SPDX-License-Identifier: Apache-2.0
"""Leaks and bugs the privacy runs found in other packages, each pinned as a strict xfail.

The ids match ``NOTES-privacy.md``. A fix elsewhere turns the xfail into an unexpected pass, which
fails the suite until the marker is removed.
"""

from __future__ import annotations

import pytest

from coalitionkit_acceptance.privacy_collect import ECHO, Observer, steward_pass
from coalitionkit_acceptance.privacy_mcp import HostBackedPorts, McpRun
from coalitionkit_acceptance.privacy_world import PrivacyWorld
from coalitionkit_acceptance.scanner import scan


@pytest.mark.xfail(
    strict=True, reason="PRIV-1: the Steward passes a model's reason into the verdict unfiltered"
)
async def test_priv1_steward_verdict_text_carries_no_redacted_field() -> None:
    world = PrivacyWorld(7)
    world.build()
    await steward_pass(world, ECHO)
    world.arena.close()
    leaks = [x for x in scan(world.ledger, world.registry).leaks if x.surface == "steward_verdict"]
    assert leaks == []


@pytest.mark.xfail(
    strict=True, reason="PRIV-2: an MCP write is committed but the tool reports not_authorized"
)
async def test_priv2_mcp_write_reports_success_for_a_committed_event() -> None:
    world = PrivacyWorld(4)
    world.build()
    observer = Observer(world)
    ports = HostBackedPorts(world.host, world.people, ignore)
    run = McpRun(ports, observer.tokens)
    with run.serve():
        async with run.session("p1") as session:
            text = await session.call(
                "report_ripple",
                {
                    "coalition_id": world.host.coalition_id,
                    "change": "check",
                    "invalidates": [world.tasks[2]],
                },
            )
    committed = [e for e in world.arena.events() if e["type"] == "coalition.ripple"]
    world.arena.close()
    assert len(committed) == 1
    assert "not_authorized" not in text


@pytest.mark.xfail(
    strict=True, reason="PRIV-3: the host refuses the request and response rounds of a PSI exchange"
)
def test_priv3_psi_rounds_are_relayed_in_protocol_order() -> None:
    world = PrivacyWorld(9)
    world.build()
    refusals = list(world.psi.refusals)
    world.arena.close()
    assert refusals == []


def ignore(*_args: object) -> None:
    return None
