# SPDX-License-Identifier: Apache-2.0
"""Sentence-driven cards, mapped by the host into the closed surface catalog."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from coalitionkit_surfaces import load_catalog, validate_surface
from coalitionkit_surfaces.catalog import Catalog

from .adapter import Document
from .settings import Settings

if TYPE_CHECKING:
    from .genesis_draft import DraftResponse


class CardChoice(BaseModel):
    """A choice of view; facts come from the draft, never arbitrary model props."""

    model_config = ConfigDict(extra="forbid")
    kind: Literal[
        "map", "seats", "deadline", "checklist", "availability", "week", "fairness", "cost", "route"
    ]
    word: str | None


class GraphChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["graph"]
    word: str
    steps: list[str] = Field(min_length=2, max_length=12)


class Card(BaseModel):
    id: str
    component: str
    title: str
    word: str | None
    size: Literal["hero", "wide", "half", "third"]
    props: Document


class Composition(BaseModel):
    source: Literal["reader", "model"] = "reader"
    cards: list[Card] = Field(default_factory=list[Card])


@lru_cache(maxsize=8)
def composition_catalog(path: Path | None = None) -> Catalog:
    """Reuse the server's configured catalog path, cached across draft requests."""
    return load_catalog(path or Settings().catalog_file)


WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
WEEKDAY = re.compile(r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b", re.I)
COMPONENTS = {
    "map": ("MapView", "place"),
    "seats": ("SeatRing", "seat"),
    "deadline": ("Deadline", "deadline"),
    "checklist": ("Checklist", "need"),
    "graph": ("DependencyGraph", "task"),
    "availability": ("AvailabilityGrid", "availability"),
    "week": ("CalendarWeek", "week"),
    "fairness": ("FairnessMeter", "fairness"),
    "cost": ("CostSplit", "cost"),
    "route": ("RouteCard", "route"),
}
TITLES = {
    "map": "Where",
    "seats": "Seats",
    "deadline": "Closes",
    "checklist": "What needs doing",
    "graph": "Order of work",
    "availability": "Free windows",
    "week": "This week",
    "fairness": "Who has done what",
    "cost": "Shares",
    "route": "Getting there",
}
# What the sheet is built around, in order: the first of these present leads the screen.
LEADS = ("map", "graph", "week", "route", "availability", "checklist")


def ordered_steps(goal: str) -> GraphChoice | None:
    # A conjunction alone does not imply tasks: require verbs on both sides of "and".
    verbs = r"(?:prepare|review|check|send|collect|share|write|read|plan|build|test|finish|approve)"
    clause = re.split(r"\s+(?:on|by)\s+(?=\w)|[.!?]", goal, maxsplit=1)[0]
    clause = re.sub(r"^.*?\b(?:need|needs|want|wants)\s+(?:to\s+)?", "", clause, flags=re.I)
    opening = re.match(r"([A-Z]\w+) and ([a-z]\w+)\b", clause)
    if re.search(r"\bthen\b", clause, re.I):
        parts = re.split(r"\s+(?:and\s+)?then\s+", clause, flags=re.I)
    elif opening:
        # An instruction opening on two joined words: "Do this and that ..."
        clause, parts = opening[0], [opening[1], opening[2]]
    else:
        match = re.search(rf"\b{verbs}\b.+?\s+and\s+{verbs}\b.*", clause, re.I)
        if not match:
            return None
        clause = match[0]
        parts = re.split(rf"\s+and\s+(?={verbs}\b)", clause, flags=re.I)
    steps = [part.strip(" ,") for part in parts]
    if not 2 <= len(steps) <= 12 or not all(steps):
        return None
    return GraphChoice(kind="graph", word=clause, steps=steps)


def reading_word(result: DraftResponse, kind: str) -> str | None:
    reading = next((r for r in result.reading if r.kind == kind), None)
    return result.draft.goal[slice(*reading.span)] if reading else None


def seats_word(result: DraftResponse) -> str | None:
    """The count and the role together, as the sentence says them: "Twelve of us"."""
    spans = [r.span for r in result.reading if r.kind in {"count", "role"}]
    if not spans:
        return None
    first = min(spans)
    following = [span for span in spans if span[0] >= first[1]]
    end = min(following)[1] if following else first[1]
    return result.draft.goal[first[0] : end]


def reader_choices(result: DraftResponse) -> list[CardChoice | GraphChoice]:
    draft = result.draft
    choices: list[CardChoice | GraphChoice] = []
    for kind, present, word in [
        ("map", draft.place is not None, draft.place),
        ("deadline", draft.deadline is not None, reading_word(result, "deadline")),
        ("checklist", bool(draft.needs), reading_word(result, "need")),
    ]:
        if present:
            choices.append(CardChoice.model_validate({"kind": kind, "word": word}))
    if graph := ordered_steps(draft.goal):
        choices.append(graph)
    if weekday := WEEKDAY.search(draft.goal):
        choices.append(CardChoice(kind="week", word=weekday[0]))
    if fair := re.search(r"\bfair(?:ly|ness)?\b", draft.goal, re.I):
        choices.append(CardChoice(kind="fairness", word=fair[0]))
    return choices


def card_props(choice: CardChoice | GraphChoice, result: DraftResponse) -> Document:
    draft = result.draft
    match choice.kind:
        case "seats":
            return {
                "goal": ", ".join(role.label for role in draft.roles),
                "seats": [],
                "openSeats": {
                    "value": sum(role.count for role in draft.roles),
                    "event_ref": "draft:roles",
                },
            }
        case "map":
            return {"points": [], "routes": [], "areas": []}
        case "deadline":
            props: Document = {
                "label": (choice.word or "Closes").capitalize(),
                "consequence": "The code stops working then.",
            }
            if draft.deadline:
                props["deadline"] = draft.deadline.isoformat()
            return props
        case "checklist":
            return {"items": [{"text": need, "done": False} for need in draft.needs]}
        case "graph":
            assert isinstance(choice, GraphChoice)
            return {
                "nodes": [
                    {"task": str(i + 1), "title": step, "status": "open"}
                    for i, step in enumerate(choice.steps)
                ],
                "edges": [
                    {"from": str(i + 1), "to": str(i + 2)} for i in range(len(choice.steps) - 1)
                ],
            }
        case "availability":
            return {
                "days": [{"id": m[0].lower(), "label": m[0]} for m in WEEKDAY.finditer(draft.goal)],
                "slots": [],
            }
        case "week":
            return week_props(draft.goal)
        case "fairness":
            return {
                "rows": [
                    {
                        "participant": role.label,
                        "hours": {"value": 0, "event_ref": "draft:roles"},
                        "share": {"value": 0, "event_ref": "draft:roles"},
                    }
                    for role in draft.roles
                ]
            }
        case "cost":
            return {"items": []}
        case "route":
            return {"steps": [], "participants": []}


def week_props(goal: str) -> Document:
    """The week around the day the sentence names, with that day marked and no hour claimed."""
    today = datetime.now(UTC).date()
    named = WEEKDAY.search(goal)
    if not named:
        return {"events": [], "range": {"start": today.isoformat()}}
    ahead = (WEEKDAYS.index(named[0].lower()) - today.weekday()) % 7
    day = today + timedelta(days=ahead)
    first = today if ahead < 5 else day - timedelta(days=4)
    return {
        "range": {"start": first.isoformat()},
        "events": [
            {
                "kind": "task",
                "task": named[0].capitalize(),
                "state": "scheduled",
                "start": f"{day.isoformat()}T09:00:00Z",
                "end": f"{day.isoformat()}T17:00:00Z",
                "assignee": "",
            }
        ],
    }


def pack_title(vocabulary: Document, term: str) -> str | None:
    """A pack's own word for a card, plural where it has one."""
    word = vocabulary.get(term)
    if isinstance(word, dict):
        forms = cast("dict[str, object]", word)
        word = forms.get("other") or forms.get("one")
    return word if isinstance(word, str) else None


def card_errors(card: Card, catalog: Catalog) -> list[str]:
    return validate_surface(
        catalog,
        catalog.catalog_id,
        [{"id": "root", "component": card.component, **card.props}],
        known_events={"draft:roles"},
    )


def build_cards(
    result: DraftResponse, choices: list[CardChoice | GraphChoice], catalog: Catalog
) -> list[Card]:
    cards: list[Card] = []
    seats = CardChoice(kind="seats", word=seats_word(result))
    for choice in [seats, *(c for c in choices if c.kind != "seats")]:
        if any(card.id == choice.kind for card in cards):
            continue
        if choice.word is not None and (not choice.word or choice.word not in result.draft.goal):
            raise ValueError("card word is not in goal")
        if isinstance(choice, GraphChoice):
            cursor = 0
            for step in choice.steps:
                at = choice.word.find(step, cursor)
                if not step or at < 0:
                    raise ValueError("steps are not ordered goal substrings")
                cursor = at + len(step)
        component, term = COMPONENTS[choice.kind]
        title = pack_title(result.vocabulary, term)
        card = Card(
            id=choice.kind,
            component=component,
            title=title.capitalize() if title else TITLES[choice.kind],
            word=choice.word,
            size="third",
            props=card_props(choice, result),
        )
        if not card_errors(card, catalog):
            cards.append(card)
        elif result.model_cards:
            raise ValueError("invalid model card")
        if len(cards) == 6:
            break
    if not any(card.component == "SeatRing" for card in cards):
        # Unsafe role labels must not remove the mandatory, factual open-seat count.
        card = Card(
            id="seats",
            component="SeatRing",
            title=TITLES["seats"],
            word=None,
            size="third",
            props={
                "seats": [],
                "openSeats": {
                    "value": sum(r.count for r in result.draft.roles),
                    "event_ref": "draft:roles",
                },
            },
        )
        if card_errors(card, catalog):
            raise ValueError("catalog cannot represent draft seats")
        cards.insert(0, card)
    return arrange(cards[:6])


# How many cards are left, and the sizes that fill rows of twelve columns exactly.
ROWS: dict[int, list[Literal["wide", "half", "third"]]] = {
    0: [],
    1: ["wide"],
    2: ["half", "half"],
    3: ["third", "third", "third"],
    4: ["half", "half", "half", "half"],
    5: ["third", "third", "third", "half", "half"],
    6: ["third", "third", "third", "third", "third", "third"],
}


def arrange(cards: list[Card]) -> list[Card]:
    """Build the sheet around what this sentence is about, filling each row of twelve columns."""
    lead = next((k for k in LEADS if any(card.id == k for card in cards)), None)
    ordered = sorted(cards, key=lambda card: (card.id != lead, card.id != "seats"))
    if lead is None:
        rest = ordered
    else:
        head, rest = ordered[0], ordered[1:]
        # A sequence reads across the page; anything else takes the big square beside two cards.
        head.size = "wide" if lead in {"graph", "route"} or len(rest) < 2 else "hero"
        if head.size == "hero":
            for card in rest[:2]:
                card.size = "third"
            rest = rest[2:]
    for card, size in zip(rest, ROWS[len(rest)], strict=True):
        card.size = size
    return ordered


def compose_draft(result: DraftResponse, catalog: Catalog | None = None) -> Composition:
    catalog = catalog or composition_catalog()
    if result.model_cards:
        try:
            # What the reader found stays: the model adds to it and never loses a place or a step.
            chosen = {choice.kind for choice in result.model_cards}
            found = [choice for choice in reader_choices(result) if choice.kind not in chosen]
            return Composition(
                source="model", cards=build_cards(result, [*result.model_cards, *found], catalog)
            )
        except ValueError, TypeError:
            result.model_cards = []
    return Composition(cards=build_cards(result, reader_choices(result), catalog))
