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
from .brief import given
from .engine import FOR_YOU
from .model import ask
from .needs import tidy
from .offer_rules import limits, span
from .seats import people, read_state

if TYPE_CHECKING:
    from .engine import RoomEngine

NAME_MAX = 40
LINE_MAX = 260

NAMES_SYSTEM = (
    "You are the Gardener of a small group room. For each plan, write a short public name "
    "(under 30 characters, no quotes) and one plain line of under 160 characters saying what "
    "the plan trades, from the numbers given: total_minutes (time in all), busiest_minutes "
    "(how evenly the work is shared) and effort_points (how well it fits what people "
    "prefer; lower is better). best_at lists what each plan is best at among these plans. "
    "Name a plan by what it favours, and do not add facts that are not in the data."
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
TRADES = (
    ("minutes", "the least time in all"),
    ("busiest", "the most even load"),
    ("effort", "the most people on what they prefer"),
)
NAMES = {"minutes": "Fastest", "busiest": "Most even", "effort": "Most preferred"}


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


def mark_best(shown: list[Document]) -> None:
    """Say, on each plan, what it is best at among these plans (nothing when all are equal)."""
    keys = {"minutes": "total_minutes", "busiest": "busiest_minutes", "effort": "effort_points"}
    for item in shown:
        item["best_at"] = []
    for trade, key in keys.items():
        values = [item[key] for item in shown]
        if len(set(values)) < 2:
            continue
        for item in shown:
            if item[key] == min(values):
                item["best_at"].append(trade)


def rule_note(index: int, shown: Document) -> Document:
    best = [t for t, _ in TRADES if t in shown["best_at"]]
    name = " and ".join(NAMES[t] for t in best[:2]) if best else f"Plan {chr(65 + index)}"
    wins = "; ".join(dict(TRADES)[t] for t in best)
    line = (
        f"{shown['total_minutes']} minutes in all, the busiest person carries "
        f"{shown['busiest_minutes']}, effort {shown['effort_points']}."
    )
    return {
        "name": name,
        "line": f"{line} Gives {wins}." if wins else line,
        "source": "rules",
    }


def over_limit(who: str, plan: Document, state: State, cap: int | None) -> str:
    """Said by code, not the model: the plan asks more of them than the hours they gave."""
    asked = sum(
        minutes_of(state, who, a["task_id"]) for a in plan["assignments"] if a["assignee"] == who
    )
    if cap is None or asked <= cap:
        return ""
    return f" This asks {span(asked)} of your {span(cap)}."


def rule_for_you(who: str, plan: Document, titles: dict[str, str], state: State) -> str:
    mine = [a for a in plan["assignments"] if a["assignee"] == who]
    if not mine:
        return "In this plan you take nothing on; others carry the work."
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
    mark_best(shown)
    reply = await ask(
        engine,
        coalition,
        "gardener",
        NAMES_SYSTEM,
        {"goal": state.charter["goal"], "plans": shown},
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
            if name and line
            else rule_note(index, item)
        )
    engine.update(coalition, lambda d: d["plan_notes"].update(notes))


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
        said = wording.get(plan["plan_id"])
        line = said or rule_for_you(who, plan, titles, state)
        lines[plan["plan_id"]] = {
            "line": line + over_limit(who, plan, state, cap),
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
    if fresh:
        await name_plans(engine, coalition, state, fresh, doc)
    hosted = [p for p in people(state, doc) if engine.is_hosted(coalition, p)]
    await asyncio.gather(*(for_you(engine, coalition, who, state, plans, doc) for who in hosted))
