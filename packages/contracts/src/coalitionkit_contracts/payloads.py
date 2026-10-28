# SPDX-License-Identifier: Apache-2.0
"""Payload models, one per message type. They mirror spec/schemas/coalition/v0/*.json."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, Field, StringConstraints

from ._types import (
    DetachedJws,
    Id,
    Money,
    PayloadPath,
    PositiveInt,
    Revision,
    Rfc3339,
    SafeInt,
    Sha256Hex,
    Text,
    Ulid,
    UniqueIds,
    UniqueUlids,
    Uri,
    WireModel,
    check_unique,
)

Effort = Literal["low", "medium", "high"]

#: ``coalition.query`` deadline when ``deadline_ms`` is omitted.
DEFAULT_QUERY_DEADLINE_MS = 10_000
#: Most elements either side may put into a PSI exchange.
PSI_MAX_ELEMENTS = 1024
#: Longest ``coalition.match`` blob: a response holds two framed lists of 32-byte elements.
PSI_MAX_BLOB_CHARS = 94_000


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
    id: Ulid


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
    deciders: Annotated[UniqueIds, Field(min_length=1)]
    revision: Revision
    created_at: Rfc3339
    pack: PackRef | None = None
    budget: Budget | None = None
    count_trusted: UniqueIds | None = None


class Ed25519Jwk(WireModel):
    kty: Literal["OKP"]
    crv: Literal["Ed25519"]
    x: Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{43}$")]
    kid: Id


class JoinPayload(WireModel):
    card_url: Uri
    owner_key: Ed25519Jwk
    owner_proof: DetachedJws
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
    need_id: Ulid
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
    deadline_ms: PositiveInt = DEFAULT_QUERY_DEADLINE_MS


class AnswerPayload(WireModel):
    query_id: Id
    result: Literal["yes", "no"] | Cost


class MatchPayload(WireModel):
    match_id: Id
    peer: Id
    round: Literal["setup", "request", "response"]
    blob: Annotated[
        str, StringConstraints(pattern=r"^[A-Za-z0-9_-]*$", max_length=PSI_MAX_BLOB_CHARS)
    ]
    reveal: Literal["overlap", "count"]


class Assignment(WireModel):
    task_id: Ulid
    assignee: Id


class Plan(WireModel):
    plan_id: Ulid
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
    tension_id: Ulid
    revision: Revision
    options: Annotated[list[TensionOption], Field(min_length=2)]
    tradeoffs: list[Text]
    deciders: Annotated[UniqueIds, Field(min_length=1)]


class Subject(WireModel):
    kind: Literal["plan", "tension_option", "commitment", "charter", "task"]
    id: Ulid
    revision: Revision


class DecidePayload(WireModel):
    subject: Subject
    choice: Id
    consent: bool
    decided_at: Rfc3339
    consent_sig: DetachedJws


class CommitPayload(WireModel):
    commitment_id: Ulid
    task_id: Ulid
    status: Literal["pending", "withdrawn"]
    revision: Revision | None = None


class RipplePayload(WireModel):
    change: Text
    invalidates: UniqueUlids


class Evidence(WireModel):
    kind: Id
    ref: Id
    verified_by: Id


class DonePayload(WireModel):
    task_id: Ulid
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
    "duplicate_mismatch",
    "not_authorized",
]


class ErrorDetail(WireModel):
    message: str | None = None
    policy_id: Id | None = None
    retry_after_ms: SafeInt | None = None


class ErrorPayload(WireModel):
    code: ErrorCode
    detail: ErrorDetail
    ref: Ulid


class ProjectionSource(WireModel):
    event_id: Ulid
    seq: PositiveInt
    type: Annotated[str, StringConstraints(pattern=r"^coalition\.[a-z_]+$")]
    on_behalf_of: Id


class ProjectionPayload(WireModel):
    source: ProjectionSource
    payload: dict[str, Any]
    redacted: Annotated[list[PayloadPath], AfterValidator(check_unique)] | None = None


class ReceiptPayload(WireModel):
    coalition_id: Ulid
    seq: PositiveInt
    head_hash: Sha256Hex


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
    "coalition.projection": ProjectionPayload,
    "coalition.receipt": ReceiptPayload,
    "coalition.error": ErrorPayload,
}

#: The eighteen message types of v0.1 (coalition.error is a payload, not one of the eighteen).
MESSAGE_TYPES: tuple[str, ...] = tuple(t for t in PAYLOAD_MODELS if t != "coalition.error")

#: Types only the host sends; a member that sends one gets ``not_authorized``.
HOST_ONLY_TYPES: frozenset[str] = frozenset(
    f"coalition.{name}"
    for name in (
        "charter",
        "need",
        "query",
        "propose",
        "tension",
        "dissolve",
        "projection",
        "receipt",
    )
)
#: Types a member (or its vault or edge) may send, before the per-type authorization checks.
MEMBER_TYPES: frozenset[str] = frozenset(MESSAGE_TYPES) - HOST_ONLY_TYPES
