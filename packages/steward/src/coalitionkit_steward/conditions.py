# SPDX-License-Identifier: Apache-2.0
"""Deterministic evaluation of policies against a subject (a message or a minted artifact)."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from typing import Any, cast

from coalitionkit_contracts import Envelope, Scope

from .categories import CATEGORIES
from .policy import Policy

#: Payload keys that are private wherever they appear in an outbound message.
PRIVATE_KEYS: frozenset[str] = frozenset(
    {"phone", "email", "home_address", "iban", "ssn", "national_id", "password", "secret"}
)
#: Scopes that stay between the sender and the host.
INTERNAL_AUDIENCES = frozenset({"self", "host"})
MAX_TEXT_CHARS = 20_000


@dataclass(frozen=True)
class StewardContext:
    """Facts the host knows and the message does not carry."""

    #: Participants who have consented to being contacted.
    consented: frozenset[str] = frozenset()
    #: Extra payload paths (``payload.a.b``) that must never leave in an outbound message.
    private_paths: frozenset[str] = frozenset()
    #: How many participants share the work (the fairness check needs at least two).
    participant_count: int = 2
    #: The members of the Coalition, when the host passes them. The model audit then covers
    #: only the views of members; an assignee who is no member is shown nothing.
    members: frozenset[str] | None = None


@dataclass(frozen=True)
class Subject:
    """What the Steward looks at: an envelope, or an artifact minted from events."""

    kind: str  # "message" or "artifact"
    coalition_id: str
    event_id: str
    revision: int
    type: str
    on_behalf_of: str
    scope: Scope
    payload: dict[str, Any]

    @classmethod
    def from_envelope(cls, envelope: Envelope, revision: int = 1) -> Subject:
        return cls(
            "message",
            envelope.coalition_id,
            envelope.event_id,
            revision,
            envelope.type,
            envelope.on_behalf_of,
            envelope.scope,
            envelope.payload,
        )


@dataclass(frozen=True)
class Match:
    policy: Policy
    redact: tuple[str, ...] = ()


@dataclass
class _Eval:
    subject: Subject
    ctx: StewardContext
    redact: list[str] = field(default_factory=lambda: [])
    # Only a redact policy needs the fields a text condition matched in.
    text_paths: bool = False


def walk(value: Any, path: str = "payload") -> Iterator[tuple[str, Any]]:
    """Yield ``(path, leaf)`` for every scalar leaf of a JSON value, in order."""
    if isinstance(value, dict):
        for key, child in cast("dict[str, Any]", value).items():
            yield from walk(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(cast("list[Any]", value)):
            yield from walk(child, f"{path}.{index}")
    else:
        yield path, value


def subject_text(subject: Subject) -> str:
    # A private field (a phone, an email) is the redact policy's to mask, not text to judge.
    texts: list[str] = [
        leaf
        for path, leaf in walk(subject.payload)
        if isinstance(leaf, str) and path.rsplit(".", 1)[-1] not in PRIVATE_KEYS
    ]
    return "\n".join(texts)[:MAX_TEXT_CHARS]


def _mark_matching_fields(ev: _Eval, found: Callable[[str], bool]) -> None:
    """Record each string field a text condition matched in, so ``redact`` masks those fields."""
    if not ev.text_paths:
        return
    already = set(ev.subject.scope.redact or [])
    for path, leaf in walk(ev.subject.payload):
        if isinstance(leaf, str) and path not in already and found(leaf[:MAX_TEXT_CHARS]):
            ev.redact.append(path)


def _text_category(ev: _Eval, categories: Iterable[str]) -> bool:
    text = subject_text(ev.subject)
    compiled = [p for name in categories for p in CATEGORIES[name]]
    held = any(p.search(text) for p in compiled)
    if held:
        _mark_matching_fields(ev, lambda leaf: any(p.search(leaf) for p in compiled))
    return held


def _text_pattern(ev: _Eval, patterns: Iterable[str]) -> bool:
    text = subject_text(ev.subject)
    listed = list(patterns)
    held = any(re.search(p, text, re.IGNORECASE) for p in listed)
    if held:
        _mark_matching_fields(
            ev, lambda leaf: any(re.search(p, leaf, re.IGNORECASE) for p in listed)
        )
    return held


def _addresses_unconsented(ev: _Eval) -> bool:
    scope = ev.subject.scope
    if scope.audience != "participants":
        return False
    return any(p not in ev.ctx.consented for p in scope.participants or [])


def _private_field(ev: _Eval) -> bool:
    scope = ev.subject.scope
    if scope.audience in INTERNAL_AUDIENCES:
        return False
    already = set(scope.redact or [])
    for path, _ in walk(ev.subject.payload):
        last = path.rsplit(".", 1)[-1]
        if (last in PRIVATE_KEYS or path in ev.ctx.private_paths) and path not in already:
            ev.redact.append(path)
    return bool(ev.redact)


def _assignees(plan: object) -> list[str]:
    if not isinstance(plan, dict):
        return []
    items: object = cast("dict[str, Any]", plan).get("assignments", [])
    if not isinstance(items, list):
        return []
    return [
        str(cast("dict[str, Any]", item).get("assignee"))
        for item in cast("list[Any]", items)
        if isinstance(item, dict)
    ]


def _share_above(ev: _Eval, cap: float) -> bool:
    if ev.subject.type != "coalition.propose" or ev.ctx.participant_count < 2:
        return False
    plans: object = ev.subject.payload.get("plans", [])
    if not isinstance(plans, list):
        return False
    for plan in cast("list[Any]", plans):
        counts = Counter(_assignees(plan))
        total = sum(counts.values())
        if total >= 2 and max(counts.values()) / total > cap:
            return True
    return False


def evaluate(policy: Policy, subject: Subject, ctx: StewardContext) -> Match | None:
    """The policy's match on the subject, or None. Every condition present must hold."""
    if subject.type not in policy.applies_to:
        return None
    ev = _Eval(subject, ctx, text_paths=policy.then == "redact")
    when = policy.when
    held = (
        when.any_text_matches_category is None
        or _text_category(ev, when.any_text_matches_category),
        when.any_text_matches is None or _text_pattern(ev, when.any_text_matches),
        when.addresses_unconsented is None
        or _addresses_unconsented(ev) is when.addresses_unconsented,
        when.private_field_in_outbound is None
        or _private_field(ev) is when.private_field_in_outbound,
        when.plan_share_above is None or _share_above(ev, when.plan_share_above),
    )
    if not all(held):
        return None
    return Match(policy, tuple(dict.fromkeys(ev.redact)))


def evaluate_all(policies: Iterable[Policy], subject: Subject, ctx: StewardContext) -> list[Match]:
    return [m for p in policies if (m := evaluate(p, subject, ctx)) is not None]
