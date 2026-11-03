# SPDX-License-Identifier: Apache-2.0
"""Plan words: plain, with people's names, and never the internals of planning."""

from __future__ import annotations

import re

from coalitionkit_server.adapter import Document
from coalitionkit_server.room import plan_words as words


def plan(pid: str, rows: list[tuple[str, str, int, str]]) -> Document:
    """A plan as the engine shows it to words: (seat, need, minutes, effort) per assignment."""
    level = {"low": 1, "medium": 2, "high": 3}
    load: dict[str, int] = {}
    for seat, _, minutes, _ in rows:
        load[seat] = load.get(seat, 0) + minutes
    return {
        "plan_id": pid,
        "assignments": [{"seat": s, "need": n, "minutes": m, "effort": e} for s, n, m, e in rows],
        "total_minutes": sum(load.values()),
        "busiest_minutes": max(load.values()),
        "effort_points": sum(level[e] for *_, e in rows),
    }


QUICK = plan("a", [("Mira", "the plan", 20, "high"), ("Jonas", "the budget", 20, "high")])
EASY = plan("b", [("Jonas", "the plan", 100, "low"), ("Mira", "the budget", 100, "low")])


def test_a_single_plan_is_named_by_who_does_what_with_no_comparison() -> None:
    note = words.rule_note(0, QUICK, [QUICK])
    assert note["name"] == "Mira and Jonas share it"
    assert note["line"] == "Mira takes the plan; Jonas takes the budget."
    alone = plan("c", [("Mira", "the plan", 20, "high")])
    assert words.rule_note(0, alone, [alone])["name"] == "Mira does it"


def test_two_plans_are_named_for_what_they_favour_and_say_what_they_give_up() -> None:
    both = [QUICK, EASY]
    first, second = (words.rule_note(i, p, both) for i, p in enumerate(both))
    assert first["name"] == "Quickest and shared evenly"
    assert second["name"] == "Suits people best"
    assert "Mira takes the plan; Jonas takes the budget." in first["line"]
    assert "asks some people for work they would rather not do" in first["line"]
    assert "takes 160 minutes longer in all" in second["line"]
    for note in (first, second):
        assert words.plain(note["name"], note["line"])
        assert not re.search(r"effort|points|best at", note["name"] + note["line"], re.I)


def test_the_facts_the_model_gets_hold_names_and_no_scores() -> None:
    told = words.facts([QUICK, EASY])
    flat = str(told)
    assert "Mira takes the plan" in flat and "the least time in all" in flat
    assert "effort_points" not in flat and "best_at" not in flat and "total_minutes" not in flat
    assert told[1]["differs_from_another_plan"] == [
        "the plan: Jonas here, Mira there",
        "the budget: Mira here, Jonas there",
    ]


def test_jargon_is_refused_so_code_writes_the_words() -> None:
    assert not words.plain("175-minute plan", "Not listed as best at any measure.")
    assert not words.plain("Quickest", "It has 4 effort points.")
    assert not words.plain("", "Mira takes the plan.")
    assert words.plain("Quickest", "Mira takes the plan; Jonas takes the budget.")
