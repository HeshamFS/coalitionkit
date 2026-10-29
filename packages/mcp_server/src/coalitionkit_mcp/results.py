# SPDX-License-Identifier: Apache-2.0
"""Tool results: rebuilt from an allowlist of fields, as structured content plus a text mirror.

Hosts copy structured content into the text the model reads, so nothing goes out that a spec did
not name. A spec is ``LEAF`` (a scalar, or a list of scalars), a dict of field specs (an object),
or a one-item tuple holding the spec of a list's elements.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Final

from mcp_types import CallToolResult, TextContent

LEAF: Final = "leaf"
JSON: Final = "json"
Spec = Any

_SCALARS = (str, int, float, bool)
_MAX_DEPTH = 6


def _scalar(value: Any) -> bool:
    return value is None or isinstance(value, _SCALARS)


def _json_copy(value: Any, depth: int) -> Any:
    """A depth-capped copy of a JSON value; anything that is not JSON becomes None."""
    if depth > _MAX_DEPTH + 4:
        return None
    if _scalar(value):
        return value
    if isinstance(value, list):
        return [_json_copy(item, depth + 1) for item in value]  # pyright: ignore[reportUnknownVariableType]
    if isinstance(value, dict):
        return {str(k): _json_copy(v, depth + 1) for k, v in value.items()}  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
    return None


def pick(value: Any, spec: Spec, _depth: int = 0) -> Any:
    """Copy ``value`` keeping only what ``spec`` names. Anything else is dropped."""
    if _depth > _MAX_DEPTH:
        return None
    if spec == JSON:
        return _json_copy(value, _depth)
    if spec == LEAF:
        if _scalar(value):
            return value
        if isinstance(value, list) and all(_scalar(item) for item in value):  # pyright: ignore[reportUnknownVariableType]
            return list(value)  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
        return None
    if isinstance(spec, tuple):
        if not isinstance(value, Sequence) or isinstance(value, str | bytes):
            return []
        items: list[Any] = []
        for item in value:  # pyright: ignore[reportUnknownVariableType]
            kept = pick(item, spec[0], _depth + 1)
            if kept is not None:
                items.append(kept)
        return items
    if isinstance(spec, dict) and isinstance(value, Mapping):
        fields: Mapping[str, Any] = value  # pyright: ignore[reportUnknownVariableType]
        out: dict[str, Any] = {}
        for name, sub in spec.items():  # pyright: ignore[reportUnknownVariableType]
            if name in fields:
                kept = pick(fields[name], sub, _depth + 1)
                if kept is not None:
                    out[str(name)] = kept  # pyright: ignore[reportUnknownArgumentType]
        return out
    return None


CHARTER: Final[dict[str, Spec]] = {
    "goal": LEAF,
    "roles": ({"id": LEAF, "required": LEAF},),
    "rules": LEAF,
    "deadline": LEAF,
    "deciders": LEAF,
    "revision": LEAF,
    "created_at": LEAF,
    "pack": {"name": LEAF, "version": LEAF},
    "budget": {"amount": LEAF, "currency": LEAF},
}
SUMMARY: Final[dict[str, Spec]] = {
    "coalition_id": LEAF,
    "goal": LEAF,
    "roles": LEAF,
    "status": LEAF,
    "revision": LEAF,
}
TASK: Final[dict[str, Spec]] = {
    "task_id": LEAF,
    "title": LEAF,
    "description": LEAF,
    "status": LEAF,
    "assignee": LEAF,
    "commitment_id": LEAF,
    "revision": LEAF,
}
QUESTION: Final[dict[str, Spec]] = {
    "query_id": LEAF,
    "kind": LEAF,
    "subject": LEAF,
    "task_id": LEAF,
    "deadline_ms": LEAF,
}
SUBJECT: Final[dict[str, Spec]] = {"kind": LEAF, "id": LEAF, "revision": LEAF}
ACK: Final[dict[str, Spec]] = {"accepted": LEAF, "event_id": LEAF, "seq": LEAF}
LOG_ENTRY: Final[dict[str, Spec]] = {
    "seq": LEAF,
    "event_id": LEAF,
    "type": LEAF,
    "ts": LEAF,
    "on_behalf_of": LEAF,
    "payload": JSON,
    "prev_hash": LEAF,
    "hash": LEAF,
    "redacted": LEAF,
    "form": LEAF,
}

STUB: Final[dict[str, Spec]] = {"seq": LEAF, "prev_hash": LEAF, "hash": LEAF}

RESULT_SPECS: Final[dict[str, dict[str, Spec]]] = {
    "list_coalitions": {"coalitions": (SUMMARY,)},
    "join_coalition": {
        **ACK,
        "coalition_id": LEAF,
        "granted_roles": LEAF,
        "charter": CHARTER,
    },
    "my_view": {
        "coalition_id": LEAF,
        "device": LEAF,
        "surface": {
            "title": LEAF,
            "status": LEAF,
            "charter_revision": LEAF,
            "tasks": (TASK,),
            "questions": (QUESTION,),
            "decisions": ({"subject": SUBJECT, "prompt": LEAF},),
            "events": ({"seq": LEAF, "type": LEAF, "payload": JSON},),
        },
    },
    "pending_questions": {"coalition_id": LEAF, "questions": (QUESTION,)},
    "answer_question": {**ACK, "query_id": LEAF},
    "make_offer": {**ACK, "offer_id": LEAF},
    "commit": {**ACK, "commitment_id": LEAF, "status": LEAF},
    "report_ripple": ACK,
    "report_done": {**ACK, "task_id": LEAF},
    "leave_coalition": ACK,
    "decide": {**ACK, "subject": SUBJECT, "choice": LEAF, "consent": LEAF},
    "approve_commitment": {**ACK, "commitment_id": LEAF, "revision": LEAF, "consent": LEAF},
    "accept_charter": {**ACK, "coalition_id": LEAF, "revision": LEAF, "consent": LEAF},
}


def mirror(summary: str, data: Mapping[str, Any]) -> str:
    """The text mirror: a one-line summary, then the same rebuilt data as compact JSON."""
    return f"{summary}\n{json.dumps(data, sort_keys=True, separators=(',', ':'))}"


def ok(
    tool: str,
    data: Mapping[str, Any],
    summary: str | Callable[[dict[str, Any]], str],
    *,
    meta: dict[str, Any] | None = None,
    readable: bool = False,
) -> CallToolResult:
    """A success result for ``tool``: ``data`` rebuilt from the tool's allowlist.

    ``summary`` is a line, or a function of the rebuilt data so the text never says more than the
    structured content. The text is the summary plus that data as JSON, or the summary alone when
    it is already a readable rendering of the data (``readable``).
    """
    rebuilt: dict[str, Any] = pick(data, RESULT_SPECS[tool])
    line = summary if isinstance(summary, str) else summary(rebuilt)
    text = line if readable else mirror(line, rebuilt)
    result = CallToolResult(content=[TextContent(text=text)], structured_content=rebuilt)
    result.meta = meta
    return result


def fail(code: str, detail: str = "") -> CallToolResult:
    """An ``isError`` result carrying the ``coalition.error`` code."""
    body: dict[str, Any] = {"code": code}
    if detail:
        body["detail"] = detail
    text = f"{code}: {detail}" if detail else code
    return CallToolResult(content=[TextContent(text=text)], structured_content=body, is_error=True)
