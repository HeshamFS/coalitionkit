# SPDX-License-Identifier: Apache-2.0
"""The read tools: ``list_coalitions``, ``my_view`` and ``pending_questions``. They send nothing."""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlparse

from mcp.server.mcpserver.context import Context
from mcp_types import CallToolResult

from coalitionkit_contracts import is_ulid

from .access import authenticate, authorize, deps_of
from .elicit import CANNOT_ASK, can_ask
from .errors import CoalitionToolError
from .results import ok

VIEW_URI = "ui://coalitionkit/surface-v1.html"


def parse_invite(invite: str) -> str:
    """The Coalition ID in an invitation: a bare ID, or a link naming it."""
    text = invite.strip()
    if is_ulid(text):
        return text
    parts = urlparse(text)
    for key in ("coalition", "coalition_id"):
        for value in parse_qs(parts.query).get(key, []):
            if is_ulid(value):
                return value
    for segment in reversed(parts.path.split("/")):
        if is_ulid(segment):
            return segment
    raise CoalitionToolError("schema_invalid", "the invite names no Coalition ID")


async def list_coalitions(ctx: Context) -> CallToolResult:
    """List the Coalitions this participant belongs to."""
    hosted = await authenticate(ctx)
    found = await deps_of(ctx).view.coalitions(hosted.participant)

    def text(data: dict[str, Any]) -> str:
        lines = [f"- {c.get('coalition_id')}: {c.get('goal', '')}" for c in data["coalitions"]]
        return "\n".join(["Your Coalitions:", *lines])

    return ok("list_coalitions", {"coalitions": found}, text)


async def pending_questions(coalition_id: str, ctx: Context) -> CallToolResult:
    """List the open questions addressed to this participant's vault."""
    hosted = await authorize(ctx, coalition_id)
    found = await deps_of(ctx).view.pending_questions(hosted.participant, coalition_id)
    data = {"coalition_id": coalition_id, "questions": found}
    return ok(
        "pending_questions",
        data,
        lambda d: f"{len(d['questions'])} open question(s) in Coalition {coalition_id}.",
    )


def event_list(surface: dict[str, Any]) -> list[dict[str, Any]]:
    """The viewer's own events as a list ordered by sequence.

    A host's projection keeps them in a map keyed by event ID; the view and the text mirror both
    want the order. Only what the viewer's projection holds is here: nothing is added.
    """
    raw: Any = surface.get("events")
    items: list[Any] = list(raw.values()) if isinstance(raw, dict) else []  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType, reportUnknownMemberType]
    if isinstance(raw, list):
        items = list(raw)  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
    found = [e for e in items if isinstance(e, dict)]  # pyright: ignore[reportUnknownVariableType]
    return sorted(found, key=lambda e: int(e.get("seq", 0)))  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType, reportUnknownVariableType]


#: How much of one entry's own text the plain-text mirror carries.
TEXT_PREVIEW = 280


def event_line(event: dict[str, Any]) -> str:
    """One log entry; a note's own text is shown, since hosts that read only text need it.

    The text comes from the same projection as the structured result, so a field the viewer may
    not see (redacted or out of scope) is already absent here.
    """
    line = f"- #{event.get('seq')} {event.get('type')}"
    payload: Any = event.get("payload")
    content: Any = payload.get("content") if isinstance(payload, dict) else None  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
    if isinstance(content, str) and content.strip():
        line += ": " + " ".join(content.split())[:TEXT_PREVIEW]
    return line


def surface_text(data: dict[str, Any]) -> str:
    """A plain-text rendering of the rebuilt surface, for hosts that render no view."""
    surface: dict[str, Any] = data.get("surface", {})
    events: list[dict[str, Any]] = surface.get("events", [])
    goal = next(
        (
            e.get("payload", {}).get("goal")
            for e in reversed(events)
            if e.get("type") == "coalition.charter"
        ),
        None,
    )
    title = surface.get("title") or goal or "Coalition"
    lines = [str(title)]
    if surface.get("status"):  # the view carries no status of its own; never invent one
        lines.append(f"Status: {surface['status']}")
    if events:
        lines.append(f"Log entries: {len(events)}")
        lines.extend(event_line(e) for e in events)
    for task in surface.get("tasks", []):
        lines.append(f"- task {task.get('task_id')}: {task.get('status')} {task.get('title', '')}")
    for question in surface.get("questions", []):
        lines.append(f"- question {question.get('query_id')} ({question.get('kind')})")
    for decision in surface.get("decisions", []):
        lines.append(f"- decision waiting: {decision.get('prompt', '')}")
    return "\n".join(lines)


def next_call(coalition_id: str, ask: dict[str, Any]) -> dict[str, Any]:
    """The exact tool call that answers one ask. The person's own answer is still what is signed."""
    kind, subject_id = str(ask.get("kind")), str(ask.get("id"))
    if kind == "charter":
        return {"tool": "accept_charter", "arguments": {"coalition_id": coalition_id}}
    if kind == "commitment":
        arguments = {"coalition_id": coalition_id, "commitment_id": subject_id}
        return {"tool": "approve_commitment", "arguments": arguments}
    subject = {"kind": kind, "id": subject_id, "revision": ask.get("revision")}
    # A tension is a vote: the choice is one of its options, not the tension itself.
    choice = "one option_id from options" if kind == "tension_option" else subject_id
    arguments = {"coalition_id": coalition_id, "subject": subject, "choice": choice}
    return {"tool": "decide", "arguments": arguments}


async def open_asks(coalition_id: str, ctx: Context) -> CallToolResult:
    """List what this participant is asked to decide right now, with the tool call for each.

    Say yes to one plan, not to every plan. Each answer is the person's own, asked at that call.
    """
    hosted = await authorize(ctx, coalition_id)
    found = await deps_of(ctx).view.open_asks(hosted.participant, coalition_id)
    asks = [
        {
            "kind": a.get("kind"),
            "id": a.get("id"),
            "revision": a.get("revision"),
            "options": a.get("options", []),
            "next_call": next_call(coalition_id, a),
        }
        for a in found
    ]
    data: dict[str, Any] = {"coalition_id": coalition_id, "asks": asks}
    if asks and not can_ask(ctx):
        data["note"] = CANNOT_ASK
    return ok(
        "open_asks",
        data,
        lambda d: (
            f"{len(d['asks'])} open ask(s) in Coalition {coalition_id}."
            + (f" {d['note']}" if "note" in d else "")
        ),
    )


async def my_view(coalition_id: str, ctx: Context, device: str = "web") -> CallToolResult:
    """Show this participant's live Coalition surface, as readable text with its data attached."""
    hosted = await authorize(ctx, coalition_id)
    if not device or len(device) > 32:
        raise CoalitionToolError("schema_invalid", "device must be 1 to 32 characters")
    surface = await deps_of(ctx).view.surface(hosted.participant, coalition_id, device)
    surface = {**surface, "events": event_list(surface)}
    data = {"coalition_id": coalition_id, "device": device, "surface": surface}
    return ok("my_view", data, surface_text, meta={"ui": {"resourceUri": VIEW_URI}}, readable=True)


__all__ = [
    "VIEW_URI",
    "list_coalitions",
    "my_view",
    "open_asks",
    "parse_invite",
    "pending_questions",
]
