# SPDX-License-Identifier: Apache-2.0
"""The maker step: the real thing a need asks for, written before anyone thinks about layout.

One call per kind, with room to think and to write. It is told to produce the finished thing from
the goal, the people, the shared times and the offers; whatever the facts do not give it must
propose concretely and keep plainly as a suggestion; it never states as fact a real venue's name,
address, phone number or a price quote. Code then checks the shape (a budget adds up to the amount
the goal states, a draft has no placeholders, a list names who brings what) and, when the model
fails, builds what it honestly can without one.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from ..adapter import Document
from .model import ask
from .needs import tidy

if TYPE_CHECKING:
    from .engine import RoomEngine

BUDGET_TOKENS = 12_000
MAKER_TIMEOUT_S = 90.0
AMOUNT = re.compile(
    r"(?:([€$£])\s*(\d[\d.,]*))|(?:(\d[\d.,]*)\s*(euros?|eur|dollars?|usd|pounds?|gbp)\b)", re.I
)
UNITS = {"€": "EUR", "$": "USD", "£": "GBP", "euro": "EUR", "euros": "EUR", "eur": "EUR"}
HEDGE = re.compile(r"^\s*(as an? (?:proposal|suggestion)|proposal|suggestion)\s*[:,]\s*", re.I)
CLOCK = re.compile(r"\b\d{1,2}:\d{2}\b|\bUTC\b|\b\d{1,2} ?(?:am|pm)\b", re.I)
PLACEHOLDER = re.compile(r"\[[^\]]{1,40}\]|<[^>]{1,40}>|\bTBD\b|lorem ipsum", re.I)

SYSTEM = (
    "You are one person's agent in a small group, making the real thing a need asks for. Write "
    "the finished thing, not a description of it, from the goal, the people (use their names), "
    "the shared times, the plan and the offers you are given. Whatever the facts do not give, "
    "propose concretely, and say once that it is a proposal; do not start every "
    "sentence with 'As a proposal'. Never state as fact a real venue's name, an "
    "address, a phone number or a price quote. Never leave a placeholder such as [name] or "
    "TBD: where something is open, say so in words. Do not invent facts the goal does not "
    "give (entry fees, programmes, guests). The shared times are only times when the people "
    "can all meet; they are not the date of the event unless the goal says so. Nothing the "
    "people said privately is given to you, so do not guess it. "
)
KIND_RULES = {
    "draft": (
        "Write a complete message someone could send as it is: a greeting, what it is about, "
        "when (the day the goal names, such as 'next Saturday'; if the goal names none, offer "
        "the shared times as options to choose from; never present shared times as a "
        "separate event; do not invent a start time or part of the day), where (a place only "
        "if the facts name one, else 'the place is still "
        "to be confirmed'), and what the reader should do next. Sign it with the people's names."
    ),
    "budget": (
        "If an amount is stated, give 3 to 8 line items that add up to exactly that amount, "
        "each with a label, a whole-number amount and who pays or how it is shared (say how it "
        "is shared in 'how_shared'). If no amount is stated, give no lines and leave "
        "'how_shared' empty."
    ),
    "place": (
        "Suggest 2 or 3 kinds of place (not named venues), each named in at most six words, with "
        "why it fits this goal and "
        "what to check first before booking it. Write the way a neighbour would say it across "
        "a table: plain, direct, one or two short sentences that end properly, no hedging "
        "such as 'it could' or 'as a proposal', and no list of tasks for named people."
    ),
    "schedule": (
        "Give the ordered steps of the plan, each a short action of at most 15 words. The times "
        "are added from the shared times; do not write times. Do not say a step is a proposal: "
        "the screen marks it."
    ),
    "list": (
        "Give 3 to 8 concrete items of at most 10 words each and, for each, who brings or does "
        "it, using the people's names, or 'anyone' when it does not matter. Do not say an item "
        "is a proposal: the screen marks it."
    ),
}


class DraftOut(BaseModel):
    subject: str
    body: str


class Line(BaseModel):
    label: str
    amount: int
    who_pays: str


class BudgetOut(BaseModel):
    lines: list[Line]
    how_shared: str


class Idea(BaseModel):
    kind_of_place: str
    why_it_fits: str
    check_first: str


class PlaceOut(BaseModel):
    ideas: list[Idea]


class Step(BaseModel):
    step: str


class ScheduleOut(BaseModel):
    steps: list[Step]


class Item(BaseModel):
    label: str
    who: str


class ListOut(BaseModel):
    items: list[Item]


SCHEMAS: dict[str, type[BaseModel]] = {
    "draft": DraftOut,
    "budget": BudgetOut,
    "place": PlaceOut,
    "schedule": ScheduleOut,
    "list": ListOut,
}


def stated_amount(goal: str) -> Document | None:
    """The amount of money the goal states ("300 euro", "€300"), as a whole number and unit."""
    found = AMOUNT.search(goal)
    if not found:
        return None
    digits = re.sub(r"[,\s]", "", found[2] or found[3])
    unit = UNITS.get((found[1] or found[4]).lower(), (found[4] or "").upper()[:3])
    try:
        value = int(float(digits))
    except ValueError:
        return None
    return {"amount": value, "unit": unit or "EUR"} if value > 0 else None


def clean_budget(out: BudgetOut, amount: int) -> Document | str:
    """Lines that add up to exactly the stated amount, or why not (so it can be asked again)."""
    lines: list[Document] = [
        {"label": tidy(x.label, 60), "amount": max(0, x.amount), "who": tidy(x.who_pays, 40)}
        for x in out.lines
        if tidy(x.label, 60)
    ][:8]
    if len(lines) < 2:
        return "give at least two line items"
    gap = amount - sum(x["amount"] for x in lines)
    if gap != 0 and abs(gap) <= max(5, amount // 20):
        lines[-1]["amount"] += gap  # a small rounding slip is fixed in the last line
        gap = 0
    if gap != 0 or any(x["amount"] <= 0 for x in lines):
        return f"the lines must add up to exactly {amount}; they add up to {amount - gap}"
    return {"lines": lines, "how_shared": tidy(out.how_shared, 200)}


def shows_free_slot(body: str, facts: Document) -> bool:
    """The text names one of the shared free slots, or a clock time the goal does not give."""
    low = body.lower()
    for slot in facts.get("common", []):
        label = str(slot["label"]).lower()
        if label and label in low:
            return True
        day = re.sub(r",?\s*\d{1,2}:\d{2}.*$", "", label).strip()
        if day and day in low:
            return True
    stated = CLOCK.findall(str(facts.get("goal", "")))
    return any(c not in stated for c in CLOCK.findall(body))


SENTENCE_HEDGE = re.compile(
    r"(?m)(^|(?<=[.!?]) )(?:as an? (?:proposal|suggestion)|proposal|suggestion) ?[:,] ?(.)", re.I
)
TALKS_ABOUT = re.compile(
    r"\b(?:a|this|the) (?:proposal|set is a proposal)\b|\bas a proposal\b", re.I
)
SAYS_PROPOSAL = re.compile(r" ?This is an? (?:proposal|suggestion)(?: for the group)?\.", re.I)
# The tail of a short line that only repeats what the screen's mark already says.
PROPOSAL_TAIL = re.compile(
    r"\W+(?:this|it|that|all this|the whole \w+|this whole \w+)\s+(?:\w+\s+)?"
    r"(?:is|are)\s+(?:an?\s+|only\s+an?\s+)?(?:proposal|suggestion|proposed|suggested)\b.*$",
    re.I,
)


def short_line(text: str, limit: int) -> str:
    """A list item or a step: whole, without a tail about being a proposal."""
    return tidy(PROPOSAL_TAIL.sub("", text.strip()), limit)


def unhedged(text: str) -> str:
    """No 'As a proposal,' opening a sentence, and no sentence that only says it is a proposal."""
    text = SAYS_PROPOSAL.sub("", text)
    text = SENTENCE_HEDGE.sub(lambda m: m[1] + m[2].upper(), text)
    kept = [
        " ".join(s for s in re.split(r"(?<=[.!?]) +", line) if not TALKS_ABOUT.search(s))
        for line in text.split(chr(10))
    ]
    return re.sub(chr(10) + "{3,}", chr(10) * 2, chr(10).join(kept)).strip()


def plain(text: str, limit: int) -> str:
    """Written like a person: no 'As a proposal,' hedges, first letter capital."""
    line = unhedged(tidy(text, limit))
    return line[:1].upper() + line[1:]


def clean(kind: str, out: BaseModel, facts: Document, names: set[str]) -> Document | str:
    """The maker's output made safe and checked, or the reason it cannot be used."""
    if isinstance(out, DraftOut):
        body = out.body.strip()
        if len(body) < 80 or PLACEHOLDER.search(body) or PLACEHOLDER.search(out.subject):
            return "write the whole message with no placeholders"
        if shows_free_slot(body, facts):
            return (
                "do not write the shared free times or any clock time: they are when the "
                "people are free, not when the event is; use the day the goal names"
            )
        return {"subject": tidy(out.subject, 100), "body": unhedged(body)[:2500]}
    if isinstance(out, BudgetOut):
        wanted = facts["amount"]
        if wanted is None:
            return {"lines": [], "how_shared": ""}
        return clean_budget(out, wanted["amount"])
    if isinstance(out, PlaceOut):
        ideas = [
            {
                "name": tidy(i.kind_of_place, 90).rstrip(". "),
                "why": plain(i.why_it_fits, 220),
                "check": plain(i.check_first, 220),
            }
            for i in out.ideas
        ]
        ideas = [i for i in ideas if i["name"] and i["why"]][:3]
        if any(shows_free_slot(f"{i['why']} {i['check']}", facts) for i in ideas):
            return "do not write the shared free times, a clock time or a deadline in the ideas"
        return {"ideas": ideas} if len(ideas) >= 2 else "give two or three kinds of place"
    if isinstance(out, ScheduleOut):
        steps = [short_line(s.step, 140) for s in out.steps if short_line(s.step, 140)][:6]
        return {"steps": steps} if steps else "give the steps"
    if isinstance(out, ListOut):
        items = [
            {
                "label": short_line(i.label, 100),
                "who": i.who if i.who in names else "anyone",
            }
            for i in out.items
            if short_line(i.label, 100)
        ][:8]
        return {"items": items} if len(items) >= 2 else "give at least two items"
    return "unusable"


async def make_data(
    engine: RoomEngine,
    coalition: str,
    kind: str,
    assignee: str,
    task: str,
    facts: Document,
) -> Document | None:
    """What the maker made, checked, or None (the caller then builds what it can by rules)."""
    names = set(facts["people"])
    shown = {k: facts[k] for k in ("goal", "need", "plan", "common", "people", "amount")}
    problem = ""
    for _ in range(2):
        out = await ask(
            engine,
            coalition,
            "composer",
            SYSTEM + KIND_RULES[kind],
            {"kind": kind, "facts": shown, "fix_this": problem},
            SCHEMAS[kind],
            verb="making",
            label=f"Making {facts['need']['title']}",
            seat=assignee,
            need=task,
            budget=BUDGET_TOKENS,
            effort="medium",
            timeout=MAKER_TIMEOUT_S,
        )
        if out is None:
            return None
        result: Any = clean(kind, out, facts, names)
        if isinstance(result, str):
            problem = result
            continue
        return result
    return None
