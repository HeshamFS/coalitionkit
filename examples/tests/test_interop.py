# SPDX-License-Identifier: Apache-2.0
"""Acceptance test 1: scripted (CI time) and live (marked, needs a key) variants."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest
from interop.rig import KEY_VARIABLE, Mode, vault_for
from interop.run import run_once
from members.kit.brain import scripted_next
from members.kit.policy import AutoOwner

OUT = Path(__file__).resolve().parent.parent / "out"
LIVE = os.environ.get("COALITIONKIT_LIVE") == "1" and bool(os.environ.get(KEY_VARIABLE))


def _assert_passed(card: dict[str, Any]) -> None:
    assert card["goal"]["reached"], card["goal"]
    assert card["messages"]["valid_share"] == 1.0, card["log"]["schema_errors"]
    assert card["log"]["signatures_ok"], card["log"]["signature_errors"]
    assert card["log"]["chain_ok"]
    assert card["canary_leaks"] == 0
    assert card["messages"]["delivery_failures"] == []
    assert card["passed"]


async def test_scripted_run_reaches_the_goal_on_three_stacks() -> None:
    card = await run_once(Mode(live=False), time_limit_s=120)
    _assert_passed(card)
    frameworks = {m["framework"] for m in card["members"].values()}
    assert frameworks == {"google-adk", "langgraph", "coalitionkit-gateway"}
    for member in card["members"].values():
        assert member["model_calls"] >= 2, member
        assert member["turn_errors"] == []
    assert card["refusals_by_code"] == {}
    assert set(card["goal"]["assignees"].values()) == {"p1", "p2", "p3"}


@pytest.mark.live
@pytest.mark.skipif(not LIVE, reason="no key (set COALITIONKIT_LIVE=1 and the Meta key)")
async def test_live_run_reaches_the_goal_on_three_stacks() -> None:
    card = await run_once(Mode(live=True), time_limit_s=420)
    OUT.mkdir(exist_ok=True)
    (OUT / "scorecard-live-pytest.json").write_text(json.dumps(card, indent=2) + "\n", "utf-8")
    _assert_passed(card)


def test_scripted_model_offers_then_commits_then_reports() -> None:
    offers = (
        'x\nFACTS: {"member": "p1", "tasks": [{"effort": "low", "label": "t1", "minutes": 3,'
        ' "money": 1, "need_id": "N1"}], "turn": "offers"}'
    )
    first = scripted_next(offers, [])
    assert first[0][0] == "make_offer"
    assert scripted_next(offers, [("make_offer", first[0][1], "accepted: ok")]) == []
    work = 'x\nFACTS: {"member": "p1", "tasks": [{"label": "t1", "task_id": "T1"}], "turn": "work"}'
    commit = scripted_next(work, [])[0]
    assert commit[0] == "commit_to_task"
    done = scripted_next(work, [(commit[0], commit[1], "approved: yes")])[0]
    assert done[0] == "report_done"
    assert scripted_next(work, [(commit[0], commit[1], "refused: stage_mismatch")]) == []


def test_vault_answers_only_yes_no_or_a_cost() -> None:
    vault = vault_for("p1")
    assert vault.answer("feasible", "t1") == "yes"
    assert vault.answer("feasible", "t2") == "no"
    assert vault.answer("availability", "t9") == "no"
    assert vault.answer("cost", "t1") == {"minutes": 30, "money": 5, "effort": "low"}
    assert vault.answer("cost", "t2") == "no"


async def test_auto_owner_accepts_a_fair_share_only() -> None:
    owner = AutoOwner(max_tasks=1)
    assert await owner.consent_plan("P", ["T1"])
    assert not await owner.consent_plan("P", ["T1", "T2"])
