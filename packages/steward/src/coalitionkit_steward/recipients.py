# SPDX-License-Identifier: Apache-2.0
"""What each recipient of a message will actually be shown, and nothing else.

The model audit sees these projections only: the payload with every redacted path removed,
and for a proposal set the assignments each recipient is entitled to. The host's own view
(the original text, vault values, fields redacted for the recipients) never reaches a model.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from copy import deepcopy
from typing import Any, cast

from .conditions import Subject

Payload = dict[str, Any]


def remove_path(value: Any, parts: list[str]) -> None:
    """Delete the ``payload.``-relative path from ``value`` in place; lists fan out."""
    if not parts:
        return
    if isinstance(value, list):
        for item in cast("list[Any]", value):
            remove_path(item, parts)
    elif isinstance(value, dict):
        mapping = cast("Payload", value)
        if len(parts) == 1:
            mapping.pop(parts[0], None)
        elif parts[0] in mapping:
            remove_path(mapping[parts[0]], parts[1:])


def redacted_payload(payload: Payload, paths: Iterable[str]) -> Payload:
    """A deep copy of ``payload`` without the ``payload.`` paths."""
    body = deepcopy(payload)
    for path in paths:
        remove_path(body, path.split(".")[1:])
    return body


def _assignee(item: object) -> str | None:
    if isinstance(item, dict):
        value: object = cast("Payload", item).get("assignee")
        return value if isinstance(value, str) else None
    return None


def _plans(body: Payload) -> list[Payload]:
    plans: object = body.get("plans")
    if not isinstance(plans, list):
        return []
    return [p for p in cast("list[Any]", plans) if isinstance(p, dict)]


def _assignments(plan: Payload) -> list[Any]:
    items: object = plan.get("assignments")
    return cast("list[Any]", items) if isinstance(items, list) else []


def _for_viewer(body: Payload, viewer: str) -> Payload:
    """A proposal set as one member sees it: only that member's own assignments."""
    mine = deepcopy(body)
    for plan in _plans(mine):
        plan["assignments"] = [a for a in _assignments(plan) if _assignee(a) == viewer]
    return mine


def _recipients(subject: Subject, body: Payload, members: frozenset[str] | None) -> list[str]:
    scope = subject.scope
    if scope.audience == "participants":
        named = list(scope.participants or [])
    else:
        found = (_assignee(i) for plan in _plans(body) for i in _assignments(plan))
        named = [a for a in found if a]
    if members is not None:
        named = [n for n in named if n in members]
    return sorted({*named, subject.on_behalf_of})


def projection_hash(payload: Payload) -> str:
    text = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(text.encode()).hexdigest()


def recipient_projections(
    subject: Subject, redact: Iterable[str], members: frozenset[str] | None = None
) -> list[Payload]:
    """The distinct payloads recipients get, deduplicated by hash, in a stable order.

    A member who holds no assignment sees a subset of every other view, so no view is made
    for them. ``redact`` is the scope's redaction list united with the Steward's own deterministic
    redactions. Recipients with the same view share one entry, so each view is audited once.
    """
    body = redacted_payload(subject.payload, [*(subject.scope.redact or []), *redact])
    if subject.type != "coalition.propose" or not _plans(body):
        return [body]
    seen: dict[str, Payload] = {}
    for viewer in _recipients(subject, body, members):
        view = _for_viewer(body, viewer)
        seen.setdefault(projection_hash(view), view)
    return list(seen.values())
