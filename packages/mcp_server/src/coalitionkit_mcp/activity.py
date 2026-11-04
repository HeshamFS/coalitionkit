# SPDX-License-Identifier: Apache-2.0
"""Report every tool call an outside agent makes, so the room can watch it work.

A server built with an ``ActivityPort`` in its ``Deps`` gets one middleware that, for each
``tools/call`` naming a Coalition, reports ``started`` before the tool runs and ``done`` or
``failed`` after, as the activity dict the rest of the kit uses (``mcp:<tool>``). The argument
line names the tool's arguments and shows only values that are public in the room anyway (need
and task ids, an offer's minutes and effort, a status); free text, answers, invitations and
evidence appear by name only. Read tools an agent polls are reported at most once a minute.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Any, cast

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.context import CallNext, ServerRequestContext

from coalitionkit_contracts import is_ulid

from .errors import split_error_text
from .ports import ActivityPort
from .tools_read import parse_invite

#: Read tools: reported at most once per ``READ_EVERY_S`` per participant, Coalition and tool.
READS = frozenset({"my_view", "open_asks", "pending_questions", "list_coalitions"})
READ_EVERY_S = 60.0
#: Arguments whose values are public in the room and short: shown as they are.
SHOWN = frozenset({"task_id", "commitment_id", "status", "capacity", "choice", "consent", "device"})
LONGEST = 40


def _map(value: Any) -> Mapping[str, Any]:
    return cast("Mapping[str, Any]", value) if isinstance(value, Mapping) else {}


def _value(key: str, value: Any) -> str | None:
    found = _map(value)
    if key == "target" and found:
        ident = found.get("id")
        return f"{found.get('kind', 'need')} {ident}" if is_ulid(ident) else None
    if key == "cost" and found:
        minutes, effort = found.get("minutes"), found.get("effort")
        if isinstance(minutes, int) and effort in {"low", "medium", "high"}:
            return f"{minutes} min, effort {effort}"
        return None
    if key == "subject" and found:
        kind, ident = found.get("kind"), found.get("id")
        return f"{kind} {ident}" if isinstance(kind, str) and is_ulid(ident) else None
    if key == "invalidates" and isinstance(value, list):
        return f"{len(cast('list[Any]', value))} needs"
    if key in SHOWN and isinstance(value, (str, int, bool)) and len(str(value)) <= LONGEST:
        return str(value)
    return None


def args_line(arguments: Mapping[str, Any]) -> str:
    """``target need 01J…, cost 30 min, effort low, capacity 1``: names, and public values only."""
    parts: list[str] = []
    for key in sorted(arguments):
        if key == "coalition_id":
            continue
        shown = _value(key, arguments[key])
        parts.append(f"{key} {shown}" if shown is not None else key)
    return ", ".join(parts)


def result_line(result: Any) -> tuple[bool, str, list[str]]:
    """``(failed, line, refs)`` from a tool result in its wire form."""
    body = _map(result)
    data = _map(body.get("structuredContent") or body.get("structured_content"))
    if body.get("isError") or body.get("is_error"):
        code = data.get("code")
        if not isinstance(code, str):
            blocks: list[Any] = list(body.get("content") or [])
            text = _map(blocks[0]).get("text") if blocks else None
            found = split_error_text(text) if isinstance(text, str) else None
            code = found[0] if found else "error"
        return True, f"refused: {code}", []
    event, seq = data.get("event_id"), data.get("seq")
    if is_ulid(event):
        return False, f"accepted at seq {seq}", [str(event)]
    return False, "ok", []


def coalition_of(arguments: Mapping[str, Any]) -> str | None:
    found = arguments.get("coalition_id")
    if is_ulid(found):
        return str(found)
    invite = arguments.get("invite")
    if isinstance(invite, str):
        try:
            return parse_invite(invite)
        except Exception:
            return None
    return None


class ToolActivity:
    """The middleware. ``participant_of`` maps the call's bearer token to its participant."""

    def __init__(self, port: ActivityPort, participant_of: Any) -> None:
        self.port = port
        self.participant_of = participant_of
        self.last_read: dict[tuple[str, str, str], float] = {}

    async def __call__(self, ctx: ServerRequestContext[Any, Any], call_next: CallNext) -> Any:
        if ctx.method != "tools/call":
            return await call_next(ctx)
        params: Mapping[str, Any] = ctx.params or {}
        name = str(params.get("name", ""))
        arguments = _map(params.get("arguments"))
        coalition = coalition_of(arguments)
        who = await self._participant()
        if coalition is None or who is None or not self._due(who, coalition, name):
            return await call_next(ctx)
        base: dict[str, Any] = {
            "seat": who,
            "agent": "mcp",
            "tool": f"mcp:{name}",
            "args": args_line(arguments),
        }
        start = await self._record(
            coalition, {**base, "result": "", "status": "started", "ms": 0, "refs": []}
        )
        began = time.monotonic()
        try:
            result = await call_next(ctx)
        except Exception as exc:
            ms = round((time.monotonic() - began) * 1000)
            failed = {**base, "result": type(exc).__name__, "status": "failed", "ms": ms}
            await self._record(coalition, {**failed, "refs": []}, start)
            raise
        failed, line, refs = result_line(result)
        status = "failed" if failed else "done"
        ms = round((time.monotonic() - began) * 1000)
        finish = {**base, "result": line, "status": status, "ms": ms, "refs": refs}
        await self._record(coalition, finish, start)
        return result

    async def _participant(self) -> str | None:
        access = get_access_token()
        if access is None:
            return None
        hosted = await self.participant_of(access.token)
        return None if hosted is None else str(hosted.participant)

    def _due(self, who: str, coalition: str, name: str) -> bool:
        if name not in READS:
            return True
        key, now = (who, coalition, name), time.monotonic()
        if now - self.last_read.get(key, -READ_EVERY_S) < READ_EVERY_S:
            return False
        self.last_read[key] = now
        return True

    async def _record(
        self, coalition: str, activity: dict[str, Any], start: str | None = None
    ) -> str | None:
        try:
            return await self.port.record(coalition, activity, start)
        except Exception:
            return None  # the trace never stops the tool
