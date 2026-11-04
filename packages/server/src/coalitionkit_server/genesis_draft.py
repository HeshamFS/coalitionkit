# SPDX-License-Identifier: Apache-2.0
"""Genesis goal reader and optional model draft."""

from __future__ import annotations

import asyncio
import os
import re
from datetime import UTC, datetime, timedelta, timezone
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from coalitionkit_models import ModelGateway

from .adapter import Document
from .genesis_compose import (
    CardChoice,
    Composition,
    GraphChoice,
    compose_draft,
)
from .packs import PackRef, Suggestion


class Goal(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    pack: PackRef | None = None
    goal: str = Field(min_length=1, max_length=500)
    # The writer's offset from UTC, so "tonight" and "by Friday" mean their evening, not UTC's.
    utc_offset_minutes: int | None = Field(default=None, ge=-840, le=840)


class Role(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")
    label: str = Field(min_length=1, max_length=64)
    count: int = Field(ge=1, le=10000, strict=True)


class Draft(Goal):
    place: str | None = None
    roles: list[Role] = Field(min_length=1)
    needs: list[str]
    deadline: datetime | None
    deciders: Literal["all"] = "all"

    @field_validator("deadline")
    @classmethod
    def utc_deadline(cls, value: datetime | None) -> datetime | None:
        if value is not None:
            if value.tzinfo is None:
                raise ValueError("deadline must include a timezone")
            return value.astimezone(UTC)
        return value

    @model_validator(mode="after")
    def unique_roles(self) -> Draft:
        if len({r.id for r in self.roles}) != len(self.roles):
            raise ValueError("duplicate roles")
        return self


# Model spend on drafts is metered here, since no coalition exists yet.
DRAFT_METER = "genesis-draft"
# How long Genesis waits for the model's draft before answering with the reader's own.
MODEL_DRAFT_BUDGET_S = 20


class Reading(BaseModel):
    model_config = ConfigDict(extra="forbid")
    span: tuple[int, int]
    kind: Literal["role", "need", "deadline", "count", "place"]


class ModelDraft(BaseModel):
    """What the model is asked for: closed objects only, so a strict JSON schema accepts it."""

    model_config = ConfigDict(extra="forbid")
    draft: Draft
    source: Literal["reader", "model"]
    reading: list[Reading]
    cards: list[CardChoice | GraphChoice] = Field(
        default_factory=list[CardChoice | GraphChoice], max_length=6
    )

    @model_validator(mode="after")
    def valid_spans(self) -> Self:
        # Spans only mark words in the goal; one outside it is dropped, never shown.
        size = len(self.draft.goal)
        self.reading = [r for r in self.reading if 0 <= r.span[0] < r.span[1] <= size]
        return self


class DraftResponse(BaseModel):
    """The draft as the host answers it, with the pack suggestion the host adds itself."""

    draft: Draft
    source: Literal["reader", "model"]
    reading: list[Reading]
    composition: Composition = Field(default_factory=Composition)
    model_cards: list[CardChoice | GraphChoice] = Field(
        default_factory=list[CardChoice | GraphChoice], exclude=True
    )
    suggested: Suggestion | None = None
    vocabulary: Document = Field(default_factory=dict)
    # Whether the model answered, and if not, why, in words a screen can show as they are.
    model_status: Literal["answered", "no_key", "timed_out", "failed"] = "answered"
    model_note: str = ""


WORDS = dict(
    zip(
        [
            "one",
            "two",
            "three",
            "four",
            "five",
            "six",
            "seven",
            "eight",
            "nine",
            "ten",
            "eleven",
            "twelve",
            "thirteen",
            "fourteen",
            "fifteen",
            "sixteen",
            "seventeen",
            "eighteen",
            "nineteen",
            "twenty",
        ],
        range(1, 21),
        strict=True,
    )
)
NUMBER = r"(?:\d+|" + "|".join(WORDS) + r"|an?|a)"
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DEADLINE = re.compile(
    rf"\b(?:tonight|today|tomorrow|by (?:{'|'.join(WEEKDAYS)}|\d{{4}}-\d{{2}}-\d{{2}})"
    rf"|in ({NUMBER}) (days?|hours?))\b",
    re.I,
)
# A place is a name after a preposition: capitalised words ("Hall 3"), or a name with a digit in it,
# perhaps after a plain noun ("door B12").
NAMED = r"(?=[\w-]*\d)(?=[\w-]*[A-Za-z])[\w-]+"
PLACE = re.compile(
    r"\b(?i:at|in|near|to|from)\s+"
    rf"((?:[a-z]+\s+(?={NAMED}))?(?:[A-Z][\w'-]*|{NAMED})"
    rf"(?:\s+(?:[A-Z][\w'-]*|{NAMED}|\d+))*)"
)


def read_place(goal: str) -> tuple[str | None, list[Reading]]:
    for match in PLACE.finditer(goal):
        if match[1].lower().split()[0] not in {*WEEKDAYS, *WORDS, "today", "tomorrow", "tonight"}:
            return match[1], [Reading(span=match.span(1), kind="place")]
    return None, []


def number(value: str) -> int:
    return int(value) if value.isdigit() else WORDS.get(value.lower(), 1)


def read_goal(
    goal: str, now: datetime | None = None, utc_offset_minutes: int | None = None
) -> DraftResponse:
    goal = Goal(goal=goal).goal
    local = timezone(timedelta(minutes=utc_offset_minutes or 0))
    now = (now or datetime.now(UTC)).astimezone(local)
    place, spans = read_place(goal)
    deadline = None
    match = DEADLINE.search(goal)
    if match:
        phrase = match[0].lower()
        try:
            if phrase.startswith("in "):
                amount = number(match[1])
                deadline = now + (
                    timedelta(days=amount)
                    if match[2].startswith("day")
                    else timedelta(hours=amount)
                )
            elif phrase.startswith("by "):
                day = phrase[3:]
                if day in WEEKDAYS:
                    deadline = now + timedelta(days=(WEEKDAYS.index(day) - now.weekday()) % 7)
                else:
                    deadline = datetime.fromisoformat(day).replace(tzinfo=local)
                deadline = deadline.replace(hour=23, minute=59, second=59, microsecond=0)
            else:
                deadline = (now + timedelta(days=int(phrase == "tomorrow"))).replace(
                    hour=23, minute=59, second=59, microsecond=0
                )
            spans.append(Reading(span=match.span(), kind="deadline"))
            deadline = deadline.astimezone(UTC)
        except ValueError, OverflowError:
            deadline = None
    roles: dict[str, Role] = {}
    # Counts tied to people/roles, never durations or quantities of requested objects.
    role_pattern = re.compile(
        rf"\b({NUMBER})\s+(of us|people|members?|participants?|labs?|couriers?|"
        r"teams?|volunteers?|organizers?|drivers?|reviewers?|groups?|businesses|business)\b",
        re.I,
    )
    for role_match in role_pattern.finditer(goal):
        label = role_match[2].lower()
        label = "member" if label in {"of us", "people", "participants", "participant"} else label
        label = "business" if label == "businesses" else label
        if label.endswith("s") and label != "business":
            label = label[:-1]
        count = min(number(role_match[1]), 10000)
        if count < 1:
            continue
        if label in roles:
            roles[label].count = min(10000, roles[label].count + count)
        else:
            roles[label] = Role(id=label, label=label, count=count)
        spans.extend(
            [
                Reading(span=role_match.span(1), kind="count"),
                Reading(span=role_match.span(2), kind="role"),
            ]
        )
    needs: list[str] = []
    need = re.search(
        r"\b(?:need|needs|want|wants)\s+(?:to\s+)?(.+?)(?=\s+(?:by|in)\b|\s+tonight\b|\s+today\b|\s+tomorrow\b|[.!?]?$)",
        goal,
        re.I,
    )
    if need:
        needs.append(need[1].strip())
        spans.append(Reading(span=need.span(1), kind="need"))
    result = DraftResponse(
        draft=Draft(
            goal=goal,
            place=place,
            roles=list(roles.values()) or [Role(id="member", label="member", count=1)],
            needs=needs,
            deadline=deadline,
        ),
        source="reader",
        reading=spans,
    )
    result.composition = compose_draft(result)
    return result


def with_reader_gaps(result: DraftResponse, reader: DraftResponse) -> DraftResponse:
    """Fill what the model left empty or at its default with what the reader found."""
    kinds: set[str] = set()
    # One default seat from the model never beats seats the sentence counted.
    alone = sum(role.count for role in result.draft.roles) <= 1
    if alone and sum(role.count for role in reader.draft.roles) > 1:
        result.draft.roles = reader.draft.roles
        kinds.update({"role", "count"})
    # A need said twice, once inside a longer form of itself, is one need.
    needs = result.draft.needs
    result.draft.needs = [
        need
        for i, need in enumerate(needs)
        if need not in needs[:i] and not any(need != o and need in o for o in needs)
    ]
    if result.draft.place is None and reader.draft.place is not None:
        result.draft.place = reader.draft.place
        kinds.add("place")
    if not result.draft.needs and reader.draft.needs:
        result.draft.needs = list(reader.draft.needs)
        kinds.add("need")
    if result.draft.deadline is None and reader.draft.deadline is not None:
        result.draft.deadline = reader.draft.deadline
        kinds.add("deadline")
    result.reading = [r for r in result.reading if r.kind not in kinds] + [
        r for r in reader.reading if r.kind in kinds
    ]
    return result


def noted(
    fallback: DraftResponse, status: Literal["no_key", "timed_out", "failed"], note: str
) -> DraftResponse:
    fallback.model_status, fallback.model_note = status, note
    return fallback


async def draft_goal(
    goal: str, gateway: ModelGateway, utc_offset_minutes: int | None = None
) -> DraftResponse:
    fallback = read_goal(goal, utc_offset_minutes=utc_offset_minutes)
    local_now = datetime.now(UTC).astimezone(timezone(timedelta(minutes=utc_offset_minutes or 0)))
    if not os.environ.get("COALITIONKIT_META_API_KEY"):
        return noted(
            fallback, "no_key", "No model is set up here, so only the built-in reader ran."
        )
    try:
        async with asyncio.timeout(MODEL_DRAFT_BUDGET_S):
            reply = await gateway.complete(
                "gardener",
                [
                    {
                        "role": "system",
                        "content": "Read a coalition goal into the requested JSON schema. "
                        "Preserve the goal exactly. "
                        "Use character offsets into that goal for reading spans. Give deadlines in "
                        "UTC, reading day words in the writer's local time, now "
                        f"{local_now.isoformat()}. "
                        "List each thing the goal asks to get done as a need, in the goal's "
                        "words. Default role member, count 1. "
                        "Use deciders all, pack null, source model. Never invent a deadline. "
                        "Place is the exact place name in the goal, or null. "
                        "Choose at most six cards from the closed kinds. Each word is an exact "
                        "goal substring, or null if unknown. Graph steps are ordered exact "
                        "substrings of its word. Use map for a place, seats for roles, deadline "
                        "for a deadline, checklist for needs, week for weekdays, fairness for "
                        "fairness, graph for ordered steps, availability for availability, cost "
                        "for costs and route for a route. Never invent facts or measurements.",
                    },
                    {"role": "user", "content": fallback.draft.goal},
                ],
                response_schema=ModelDraft,
                reasoning_effort="minimal",  # a short extraction; the reader answers otherwise
                coalition_id=DRAFT_METER,
            )
            parsed = ModelDraft.model_validate_json(reply.text)
            result = DraftResponse.model_validate(parsed.model_dump(exclude={"cards"}))
            result.model_cards = parsed.cards
            if result.draft.goal != fallback.draft.goal:
                raise ValueError("model changed goal")
            result.source = "model"
            if result.draft.place is not None and result.draft.place not in fallback.draft.goal:
                raise ValueError("model invented place")
            result = with_reader_gaps(result, fallback)
            result.composition = compose_draft(result)
            return result
    except TimeoutError:
        return noted(
            fallback,
            "timed_out",
            f"The model did not answer in {MODEL_DRAFT_BUDGET_S:g} seconds, so the built-in "
            "reader's reading is shown.",
        )
    except Exception:
        return noted(
            fallback, "failed", "The model's answer could not be used, so the built-in reader ran."
        )
