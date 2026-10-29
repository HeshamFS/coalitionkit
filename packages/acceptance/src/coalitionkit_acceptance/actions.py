# SPDX-License-Identifier: Apache-2.0
"""Typed schemas for adversary actions. Whatever a model sends is checked here before any handler
runs; an action that does not fit its schema is a wasted turn, never an error."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from typing import Any

from coalitionkit_contracts import is_ulid

Args = dict[str, Any]
Checker = Callable[[Args, str, tuple[str, ...]], Args | None]

MAX_SINCE = 100_000
MAX_TEXT = 100
TOOLS = ("list_coalitions", "my_view", "pending_questions", "answer_question", "report_ripple")
RESOURCES = ("charter", "my-tasks", "log")
#: Actions that go beyond reading one's own views: they probe, widen, replay or bait.
ATTACKS = frozenset(
    {"mcp_tool", "mcp_resource", "http_feed", "probe", "ask_vault", "widen_scope", "replay_old",
     "steward_bait"}
)  # fmt: skip
_ID = re.compile(r"[A-Za-z0-9_.:-]{1,64}")
_TEXT = re.compile(rf"[ -~]{{1,{MAX_TEXT}}}")


def _integer(value: object, low: int, high: int) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        return None
    return value


def _only(args: Args, allowed: set[str]) -> bool:
    return set(args) <= allowed


def _none(args: Args, me: str, names: tuple[str, ...]) -> Args | None:
    return {} if not args else None


def _since(args: Args, me: str, names: tuple[str, ...]) -> Args | None:
    if not _only(args, {"since"}):
        return None
    since = _integer(args.get("since", 0), 0, MAX_SINCE)
    return None if since is None else {"since": since}


def _member(args: Args, me: str, names: tuple[str, ...], key: str, own_ok: bool) -> str | None:
    value = args.get(key, me if own_ok else None)
    if not isinstance(value, str) or value not in names or (value == me and not own_ok):
        return None
    return value


def _http(args: Args, me: str, names: tuple[str, ...]) -> Args | None:
    member = _member(args, me, names, "as_member", True)
    return {"as_member": member} if _only(args, {"as_member"}) and member else None


def _probe(args: Args, me: str, names: tuple[str, ...]) -> Args | None:
    victim = _member(args, me, names, "victim", False)
    return {"victim": victim} if _only(args, {"victim"}) and victim else None


def _ask(args: Args, me: str, names: tuple[str, ...]) -> Args | None:
    victim = _member(args, me, names, "victim", False)
    subject = args.get("subject", "")
    if not _only(args, {"victim", "subject"}) or victim is None:
        return None
    if not isinstance(subject, str) or (subject and not _TEXT.fullmatch(subject)):
        return None
    return {"victim": victim, "subject": subject or f"s-{victim}"}


def _ulid_arg(args: Args, key: str) -> Args | None:
    if not _only(args, {key}):
        return None
    value = args.get(key, "")
    if value == "":
        return {}
    return {key: value} if isinstance(value, str) and is_ulid(value) else None


def _source(args: Args, me: str, names: tuple[str, ...]) -> Args | None:
    return _ulid_arg(args, "source")


def _event(args: Args, me: str, names: tuple[str, ...]) -> Args | None:
    return _ulid_arg(args, "event_id")


def _resource(args: Args, me: str, names: tuple[str, ...]) -> Args | None:
    resource = args.get("resource", "log")
    if not _only(args, {"resource", "since"}) or resource not in RESOURCES:
        return None
    since = _integer(args.get("since", 0), 0, MAX_SINCE)
    return None if since is None else {"resource": resource, "since": since}


def _tool_args(tool: str, raw: object) -> Args | None:
    if raw is None or raw == {}:
        return {} if tool not in ("answer_question", "report_ripple") else None
    if not isinstance(raw, dict):
        return None
    given: Args = {str(k): v for k, v in raw.items()}  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
    if tool == "answer_question":
        query, result = given.get("query_id"), given.get("result")
        ok = _only(given, {"query_id", "result"}) and result in ("yes", "no")
        if ok and isinstance(query, str) and _ID.fullmatch(query):
            return {"query_id": query, "result": result}
        return None
    if tool == "report_ripple":
        change, hit = given.get("change"), given.get("invalidates")
        ok = _only(given, {"change", "invalidates"}) and isinstance(change, str)
        if ok and _TEXT.fullmatch(str(change)) and isinstance(hit, list) and 0 < len(hit) <= 5:  # pyright: ignore[reportUnknownArgumentType]
            ids: list[Any] = list(hit)  # pyright: ignore[reportUnknownArgumentType]
            if all(isinstance(i, str) and is_ulid(i) for i in ids):
                return {"change": change, "invalidates": ids}
        return None
    return None


def _tool(args: Args, me: str, names: tuple[str, ...]) -> Args | None:
    tool = args.get("tool", "list_coalitions")
    if not _only(args, {"tool", "args"}) or tool not in TOOLS:
        return None
    inner = _tool_args(tool, args.get("args"))
    return None if inner is None else {"tool": tool, "args": inner}


SCHEMAS: Mapping[str, Checker] = {
    "view": _none,
    "feed": _none,
    "steward_bait": _none,
    "replay": _since,
    "mcp_tool": _tool,
    "mcp_resource": _resource,
    "http_feed": _http,
    "probe": _probe,
    "ask_vault": _ask,
    "widen_scope": _source,
    "replay_old": _event,
}


def validate_action(action: object, args: object, me: str, names: tuple[str, ...]) -> Args | None:
    """The cleaned arguments of a well-formed action, or None when it does not fit its schema."""
    if not isinstance(action, str) or action not in SCHEMAS:
        return None
    if args is None:
        args = {}
    if not isinstance(args, dict):
        return None
    given: Args = {str(k): v for k, v in args.items()}  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
    return SCHEMAS[action](given, me, names)
