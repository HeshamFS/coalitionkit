# SPDX-License-Identifier: Apache-2.0
"""Regression tests for PRIV-1 through PRIV-3 in NOTES-privacy.md."""

from __future__ import annotations

from coalitionkit_acceptance.privacy_collect import ECHO, Observer, steward_pass
from coalitionkit_acceptance.privacy_mcp import HostBackedPorts, McpRun
from coalitionkit_acceptance.privacy_world import PrivacyWorld
from coalitionkit_acceptance.scanner import scan


async def test_priv1_steward_verdict_text_carries_no_redacted_field() -> None:
    world = PrivacyWorld(7)
    world.build()
    await steward_pass(world, ECHO)
    world.arena.close()
    leaks = [x for x in scan(world.ledger, world.registry).leaks if x.surface == "steward_verdict"]
    assert leaks == []


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


def test_priv3_psi_rounds_are_relayed_in_protocol_order() -> None:
    world = PrivacyWorld(9)
    world.build()
    refusals = list(world.psi.refusals)
    world.arena.close()
    assert refusals == []


def ignore(*_args: object) -> None:
    return None
