# SPDX-License-Identifier: Apache-2.0
"""Explain: a name and one line for each plan, and a private "for you" line for each seat.

Plans are built by fixed rules (``plan_for``); the model only words them. The ``gardener`` role
reads public data (who takes which need, the minutes offered) and writes a public name and line
per plan. Each hosted seat's own ``hosted_agent`` writes the "for you" line and may read that
seat's vault; that line is stored in the vault and reaches only that seat. Both have fixed-rule
fallbacks, and every note records where it came from.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from pydantic import BaseModel

from coalitionkit_runtime.lifecycle import State

from ..adapter import Document
from . import plan_words as words
from .brief import given
from .engine import FOR_YOU
from .model import ask
from .needs import tidy
from .offer_rules import limits, span
from .seats import people, read_state

if TYPE_CHECKING:
    from .engine import RoomEngine

NAME_MAX = words.NAME_MAX
LINE_MAX = words.LINE_MAX

NAMES_SYSTEM = (
    "You are the Gardener of a small group room. For each plan, write a short public name "
    "(under 30 characters, no quotes) and one plain line of under 200 characters. Use the "
    "people's names exactly as given. Name a plan for what it favours (the 'favours' facts). "
    "The line says who does what, then what the plan gives up against the other plan (the "
    "'gives_up_against_the_others' facts). If there is only one plan, name it by who does "
    "what and do not compare. Say only what the facts hold; never mention points, scores, "
    "measures or what a plan is 'best at'."
)
FOR_YOU_SYSTEM = (
    "You are one person's agent in a small group room. For each plan, write one plain line "
    "telling that person what the plan means for them, in one short sentence of under 160 "
    "characters: what they would take on, and only if it matters, one thing they told you "
    "that bears on it. Say only what the data holds. Speak to them as 'you'."
)


class PlanName(BaseModel):
    plan_id: str
    name: str
    line: str


class NamesReply(BaseModel):
    plans: list[PlanName]


class PlanLine(BaseModel):
    plan_id: str
    line: str


class ForYouReply(BaseModel):
    plans: list[PlanLine]


def proposals(state: State) -> list[Document]:
    """Every plan the host has proposed, in order, with its assignments."""
    out: list[Document] = []
    for event in sorted(state.events.values(), key=lambda e: e["seq"]):
        if event["type"] == "coalition.propose":
            out.extend(event["payload"]["plans"])
    return out


def minutes_of(state: State, who: str, need: str) -> int:
    costs = [
        int(o["cost"]["minutes"])
        for o in state.offers.values()
        if o["owner"] == who and o["target"]["id"] == need
    ]
    return min(costs) if costs else 0


LEVEL = {"low": 1, "medium": 2, "high": 3}


def effort_of(state: State, who: str, need: str) -> int:
    found = [
        LEVEL[str(o["cost"]["effort"])]
        for o in state.offers.values()
        if o["owner"] == who and o["target"]["id"] == need
    ]
    return min(found) if found else 3


def public_plan(
    state: State, plan: Document, titles: dict[str, str], labels: dict[str, str]
) -> Document:
    """A plan in public terms: who does what, and the three numbers the plans trade."""
    load: dict[str, int] = {}
    effort = 0
    for a in plan["assignments"]:
        load[a["assignee"]] = load.get(a["assignee"], 0) + minutes_of(
            state, a["assignee"], a["task_id"]
        )
        effort += effort_of(state, a["assignee"], a["task_id"])
    return {
        "plan_id": plan["plan_id"],
        "assignments": [
            {
                "need": titles.get(a["task_id"], "a need"),
                "seat": labels.get(a["assignee"], a["assignee"]),
                "minutes": minutes_of(state, a["assignee"], a["task_id"]),
                "effort": next(
                    (
                        k
                        for k, v in LEVEL.items()
                        if v == effort_of(state, a["assignee"], a["task_id"])
                    ),
                    "high",
                ),
            }
            for a in plan["assignments"]
        ],
        "total_minutes": sum(load.values()),
        "busiest_minutes": max(load.values(), default=0),
        "effort_points": effort,
    }


def over_limit(who: str, plan: Document, state: State, cap: int | None) -> str:
    """Said by code, not the model: the plan asks more of them than the hours they gave."""
    asked = sum(
        minutes_of(state, who, a["task_id"]) for a in plan["assignments"] if a["assignee"] == who
    )
    if cap is None or asked <= cap:
        return ""
    return f" This asks {span(asked)} of your {span(cap)}."


NO_PART = "You have no part in this plan."


def rule_for_you(who: str, plan: Document, titles: dict[str, str], state: State) -> str:
    mine = [a for a in plan["assignments"] if a["assignee"] == who]
    if not mine:
        return NO_PART
    parts = "; ".join(
        f"{titles.get(a['task_id'], 'a need')} ({minutes_of(state, who, a['task_id'])} minutes)"
        for a in mine
    )
    return f"In this plan you take on: {parts}."


async def name_plans(
    engine: RoomEngine, coalition: str, state: State, fresh: list[Document], doc: Document
) -> None:
    from .view import seats_of

    labels = {s["seat"]: s["label"] for s in seats_of(engine, coalition, "", state, doc)}
    titles = {n["id"]: n["title"] for n in doc["needs"]}
    shown = [public_plan(state, p, titles, labels) for p in fresh]
    reply = await ask(
        engine,
        coalition,
        "gardener",
        NAMES_SYSTEM,
        {"goal": state.charter["goal"], "plans": words.facts(shown)},
        NamesReply,
        verb="explaining",
        label="Naming the plans",
    )
    wording = {p.plan_id: p for p in reply.plans} if reply else {}
    notes: Document = {}
    for index, item in enumerate(shown):
        said = wording.get(item["plan_id"])
        name, line = (tidy(said.name, NAME_MAX), tidy(said.line, LINE_MAX)) if said else ("", "")
        notes[item["plan_id"]] = (
            {"name": name, "line": line, "source": "model"}
            if words.plain(name, line)
            else words.rule_note(index, item, shown)
        )
    # Two plans never share a name: where the model gave the same one twice, code names them.
    names = [n["name"] for n in notes.values()]
    for index, item in enumerate(shown):
        if names.count(notes[item["plan_id"]]["name"]) > 1:
            notes[item["plan_id"]] = words.rule_note(index, item, shown)
            if sum(1 for n in notes.values() if n["name"] == notes[item["plan_id"]]["name"]) > 1:
                notes[item["plan_id"]]["name"] = f"Plan {chr(65 + index)}"
    engine.update(
        coalition,
        lambda d: d["plan_notes"].update(notes),
    )


async def for_you(
    engine: RoomEngine, coalition: str, who: str, state: State, plans: list[Document], doc: Document
) -> None:
    titles = {n["id"]: n["title"] for n in doc["needs"]}
    seen: Document = engine.vault(coalition, who).get(FOR_YOU, {})
    todo = [p for p in plans if p["plan_id"] not in seen]
    if not todo:
        return
    reply = await ask(
        engine,
        coalition,
        "hosted_agent",
        FOR_YOU_SYSTEM,
        {
            "person": engine.name_of(coalition, who),
            "told_by_the_person": given(engine, coalition, who),
            "plans": [
                {
                    "plan_id": p["plan_id"],
                    "your_part": [
                        {
                            "need": titles.get(a["task_id"], "a need"),
                            "minutes": minutes_of(state, who, a["task_id"]),
                        }
                        for a in p["assignments"]
                        if a["assignee"] == who
                    ],
                    "seats_taking_part": len({a["assignee"] for a in p["assignments"]}),
                }
                for p in todo
            ],
        },
        ForYouReply,
        verb="explaining",
        label="Writing what each plan means for you",
        seat=who,
        only=who,
    )
    wording = {p.plan_id: tidy(p.line, LINE_MAX) for p in reply.plans} if reply else {}
    cap = limits(given(engine, coalition, who)).cap
    lines: Document = {}
    for plan in todo:
        taking = any(a["assignee"] == who for a in plan["assignments"])
        said = wording.get(plan["plan_id"]) if taking else None
        line = said or rule_for_you(who, plan, titles, state)
        lines[plan["plan_id"]] = {
            "line": line + (over_limit(who, plan, state, cap) if taking else ""),
            "source": "model" if said else "rules",
        }
    with engine.lock:
        engine.vault_put(
            coalition, who, FOR_YOU, {**engine.vault(coalition, who).get(FOR_YOU, {}), **lines}
        )
    engine.bump(coalition)


async def advance(engine: RoomEngine, coalition: str) -> None:
    state = await read_state(engine, coalition)
    plans = proposals(state)
    if not plans:
        return
    doc = engine.read(coalition)
    fresh = [p for p in plans if p["plan_id"] not in doc["plan_notes"]]
    hosted = [p for p in people(state, doc) if engine.is_hosted(coalition, p)]
    # The plan names and each person's own line do not depend on each other: ask together.
    await asyncio.gather(
        *([name_plans(engine, coalition, state, fresh, doc)] if fresh else []),
        *(for_you(engine, coalition, who, state, plans, doc) for who in hosted),
    )
