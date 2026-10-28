# SPDX-License-Identifier: Apache-2.0
"""Payload models, one per message type. They mirror spec/schemas/coalition/v0/*.json."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from ._types import (
    Id,
    Money,
    PositiveInt,
    Revision,
    Rfc3339,
    SafeInt,
    Text,
    Ulid,
    UniqueIds,
    Uri,
    WireModel,
)

Effort = Literal["low", "medium", "high"]


class Budget(WireModel):
    amount: Money
    currency: Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]


class Cost(WireModel):
    minutes: SafeInt
    money: Money
    effort: Effort


class Window(WireModel):
    start: Rfc3339
    end: Rfc3339


class Target(WireModel):
    kind: Literal["need", "task"]
    id: Id


class CharterRole(WireModel):
    id: Id
    required: bool | None = None


class PackRef(WireModel):
    name: Id
    version: Id


class CharterPayload(WireModel):
    goal: Text
    roles: Annotated[list[CharterRole], Field(min_length=1)]
    rules: list[Text]
    deadline: Rfc3339
    pack: PackRef | None = None
    budget: Budget | None = None
    deciders: UniqueIds | None = None
    version: PositiveInt | None = None


class JoinPayload(WireModel):
    card_url: Uri
    owner_proof: Text
    roles_requested: UniqueIds
    surfaces: UniqueIds
    vault: Literal["local", "hosted"]


class LeavePayload(WireModel):
    reason: str | None = None


class ObservePayload(WireModel):
    source: Literal["voice", "camera", "chat", "device", "document"]
    content: str
    evidence_ref: Id | None = None


class NeedPayload(WireModel):
    need_id: Id
    description: Text
    requirements: list[Text]
    window: Window


class OfferPayload(WireModel):
    offer_id: Id
    target: Target
    capacity: PositiveInt
    cost: Cost
    valid_until: Rfc3339


class QueryPayload(WireModel):
    query_id: Id
    kind: Literal["feasible", "cost", "availability"]
    subject: Id
    deadline_ms: PositiveInt


class AnswerPayload(WireModel):
    query_id: Id
    result: Literal["yes", "no"] | Cost


class MatchPayload(WireModel):
    match_id: Id
    round: Literal["setup", "request", "response"]
    blob: Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]*$")]
    reveal: Literal["overlap", "count"]


class Assignment(WireModel):
    task_id: Id
    assignee: Id


class Plan(WireModel):
    plan_id: Id
    revision: Revision
    assignments: list[Assignment]
    objective_scores: dict[str, float]


class ProposePayload(WireModel):
    proposal_set_id: Id
    plans: Annotated[list[Plan], Field(min_length=1)]


class TensionOption(WireModel):
    option_id: Id
    summary: Text


class TensionPayload(WireModel):
    tension_id: Id
    revision: Revision | None = None
    options: Annotated[list[TensionOption], Field(min_length=2)]
    tradeoffs: list[Text]
    deciders: Annotated[UniqueIds, Field(min_length=1)]


class DecisionSubject(WireModel):
    kind: Literal["plan", "tension_option", "commitment"]
    id: Id
    revision: Revision


class DecidePayload(WireModel):
    subject: DecisionSubject
    choice: Id
    consent: bool


class CommitPayload(WireModel):
    commitment_id: Id
    task_id: Id
    status: Literal["pending", "approved", "withdrawn"]
    revision: Revision | None = None


class RipplePayload(WireModel):
    change: Text
    invalidates: UniqueIds


class Evidence(WireModel):
    kind: Id
    ref: Id
    verified_by: Id


class DonePayload(WireModel):
    task_id: Id
    evidence: list[Evidence]


class DissolvePayload(WireModel):
    reason: Literal["completed", "deadline", "cancelled", "budget"]
    skills_written: list[Id]


ErrorCode = Literal[
    "schema_invalid",
    "bad_signature",
    "sender_mismatch",
    "unknown_participant",
    "extension_not_activated",
    "stage_mismatch",
    "scope_violation",
    "not_a_decider",
    "stale_subject",
    "steward_blocked",
    "deadline_exceeded",
    "rate_limited",
    "budget_exhausted",
    "pack_violation",
]


class ErrorDetail(WireModel):
    message: str | None = None
    policy_id: Id | None = None
    retry_after_ms: SafeInt | None = None


class ErrorPayload(WireModel):
    code: ErrorCode
    detail: ErrorDetail
    ref: Ulid


PAYLOAD_MODELS: Mapping[str, type[WireModel]] = {
    "coalition.charter": CharterPayload,
    "coalition.join": JoinPayload,
    "coalition.leave": LeavePayload,
    "coalition.observe": ObservePayload,
    "coalition.need": NeedPayload,
    "coalition.offer": OfferPayload,
    "coalition.query": QueryPayload,
    "coalition.answer": AnswerPayload,
    "coalition.match": MatchPayload,
    "coalition.propose": ProposePayload,
    "coalition.tension": TensionPayload,
    "coalition.decide": DecidePayload,
    "coalition.commit": CommitPayload,
    "coalition.ripple": RipplePayload,
    "coalition.done": DonePayload,
    "coalition.dissolve": DissolvePayload,
    "coalition.error": ErrorPayload,
}

#: The sixteen message types of v0.1 (coalition.error is a payload, not one of the sixteen).
MESSAGE_TYPES: tuple[str, ...] = tuple(t for t in PAYLOAD_MODELS if t != "coalition.error")
