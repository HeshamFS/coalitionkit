# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownMemberType=false
"""Every tool call an outside agent makes is reported, with public values only."""

from __future__ import annotations

from typing import Any

from coalitionkit_mcp.activity import args_line, result_line
from coalitionkit_mcp.testing_rig import C1, COST, OFFER_TARGET, TASK, Rig


async def test_an_offer_is_reported_started_then_done(traced: tuple[Rig, Any]) -> None:
    rig, recorder = traced
    args = {"coalition_id": C1, "target": OFFER_TARGET, "capacity": 2, "cost": COST}
    async with rig.connect("p2") as client:
        result = await client.call_tool("make_offer", args)
    assert not result.is_error
    (c1, started, none), (c2, done, start) = recorder.seen
    assert c1 == c2 == C1 and none is None and start == started["id"]
    assert started["status"] == "started" and done["status"] == "done"
    assert started["seat"] == "p2" and started["agent"] == "mcp"
    assert started["tool"] == done["tool"] == "mcp:make_offer"
    assert done["args"] == f"capacity 2, cost 30 min, effort low, target task {TASK}"
    assert done["result"].startswith("accepted at seq ") and len(done["refs"]) == 1
    assert done["ms"] >= 0


async def test_a_refused_call_is_failed_with_its_code(traced: tuple[Rig, Any]) -> None:
    rig, recorder = traced
    async with rig.connect("p2") as client:
        bad = await client.call_tool(
            "commit", {"coalition_id": C1, "task_id": TASK, "status": "withdrawn"}
        )
    assert bad.is_error
    done = recorder.seen[-1][1]
    assert done["status"] == "failed" and done["result"] == "refused: schema_invalid"


async def test_free_text_is_named_never_shown(traced: tuple[Rig, Any]) -> None:
    rig, recorder = traced
    secret = "only mornings near the old mill"
    async with rig.connect("p2") as client:
        await client.call_tool(
            "report_ripple", {"coalition_id": C1, "change": secret, "invalidates": [TASK]}
        )
    lines = " ".join(a["args"] + a["result"] for _, a, _ in recorder.seen)
    assert "change" in lines and "invalidates 1 needs" in lines
    assert "mornings" not in lines


async def test_polled_reads_are_reported_once_a_minute(traced: tuple[Rig, Any]) -> None:
    rig, recorder = traced
    async with rig.connect("p2") as client:
        for _ in range(3):
            await client.call_tool("open_asks", {"coalition_id": C1})
    assert [a["status"] for _, a, _ in recorder.seen] == ["started", "done"]


def test_lines_hold_public_values_only() -> None:
    assert args_line({"coalition_id": C1, "invite": "https://x/join?token=abc"}) == "invite"
    assert args_line({"query_id": "q-1", "result": "yes"}) == "query_id, result"
    failed, line, refs = result_line({"isError": True, "content": [{"text": "not_authorized: x"}]})
    assert failed and line == "refused: not_authorized" and refs == []
