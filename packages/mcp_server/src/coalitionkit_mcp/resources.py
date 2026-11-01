# SPDX-License-Identifier: Apache-2.0
"""The three resources. Every read is authorized on its own and shaped by allowlists."""

from __future__ import annotations

import json
from typing import Any

from mcp.server.mcpserver.context import Context

from .access import authorize, deps_of
from .errors import CoalitionResourceError, CoalitionToolError
from .ports import HostedParticipant
from .results import CHARTER, LOG_ENTRY, STUB, TASK, pick

CHARTER_URI = "coalition://{id}/charter"
TASKS_URI = "coalition://{id}/my-tasks"
LOG_URI = "coalition://{id}/log{?since}"


async def _authorized(ctx: Context, coalition_id: str) -> HostedParticipant:
    try:
        return await authorize(ctx, coalition_id)
    except CoalitionToolError as exc:
        raise CoalitionResourceError(exc.code, exc.detail) from exc


def _dump(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


async def charter(id: str, ctx: Context) -> str:
    """The current charter."""
    hosted = await _authorized(ctx, id)
    found = await deps_of(ctx).view.charter(hosted.participant, id)
    if found is None:
        raise CoalitionResourceError("not_authorized", "no charter visible to you")
    return _dump({"coalition_id": id, "charter": pick(found, CHARTER)})


async def my_tasks(id: str, ctx: Context) -> str:
    """The tasks assigned to this participant."""
    hosted = await _authorized(ctx, id)
    found = await deps_of(ctx).view.my_tasks(hosted.participant, id)
    return _dump({"coalition_id": id, "tasks": pick(found, (TASK,))})


def log_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """A log entry rebuilt from allowlists: a stub keeps only its place in the hash chain."""
    if "type" not in entry or entry.get("form") == "stub":
        return pick(entry, STUB)
    return pick(entry, LOG_ENTRY)


async def log(id: str, ctx: Context, since: str = "0") -> str:
    """Log entries after ``since``: originals, projections, or stubs outside the caller's scope."""
    hosted = await _authorized(ctx, id)
    if not since.isdigit() or len(since) > 15:
        raise CoalitionResourceError("schema_invalid", "since must be a sequence number")
    found = await deps_of(ctx).view.log(hosted.participant, id, int(since))
    entries = [log_entry(e) for e in found if int(e.get("seq", 0)) > int(since)]
    return _dump({"coalition_id": id, "since": int(since), "entries": entries})


SKILLS_URI = "coalition://{id}/skills"


async def skills(id: str, ctx: Context) -> str:
    """Pack skills and lessons visible to the authenticated member."""
    hosted = await _authorized(ctx, id)
    port = deps_of(ctx).skills
    found = await port.skills(hosted.participant, id) if port else []
    return _dump(
        {
            "coalition_id": id,
            "skills": [{key: item[key] for key in ("name", "title", "text")} for item in found],
        }
    )
