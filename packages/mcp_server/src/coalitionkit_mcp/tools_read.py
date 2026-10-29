# SPDX-License-Identifier: Apache-2.0
"""The read tools: ``list_coalitions``, ``my_view`` and ``pending_questions``. They send nothing."""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlparse

from mcp.server.mcpserver.context import Context
from mcp_types import CallToolResult

from coalitionkit_contracts import is_ulid

from .access import authenticate, authorize, deps_of
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


def surface_text(data: dict[str, Any]) -> str:
    """A plain-text rendering of the rebuilt surface, for hosts that render no view."""
    surface: dict[str, Any] = data.get("surface", {})
    lines = [str(surface.get("title", "Coalition")), f"Status: {surface.get('status', 'unknown')}"]
    for task in surface.get("tasks", []):
        lines.append(f"- task {task.get('task_id')}: {task.get('status')} {task.get('title', '')}")
    for question in surface.get("questions", []):
        lines.append(f"- question {question.get('query_id')} ({question.get('kind')})")
    for decision in surface.get("decisions", []):
        lines.append(f"- decision waiting: {decision.get('prompt', '')}")
    return "\n".join(lines)


async def my_view(coalition_id: str, ctx: Context, device: str = "web") -> CallToolResult:
    """Show this participant's live Coalition surface, as readable text with its data attached."""
    hosted = await authorize(ctx, coalition_id)
    if not device or len(device) > 32:
        raise CoalitionToolError("schema_invalid", "device must be 1 to 32 characters")
    surface = await deps_of(ctx).view.surface(hosted.participant, coalition_id, device)
    data = {"coalition_id": coalition_id, "device": device, "surface": surface}
    return ok("my_view", data, surface_text, meta={"ui": {"resourceUri": VIEW_URI}}, readable=True)


__all__ = ["VIEW_URI", "list_coalitions", "my_view", "parse_invite", "pending_questions"]
