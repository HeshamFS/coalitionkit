# SPDX-License-Identifier: Apache-2.0
"""What a server holds, and the per-call authorization every tool and resource starts with.

The 2026-07-28 spec is stateless: nothing from an earlier call is trusted. Each call maps its
bearer token to one participant and asks the ViewPort whether that participant is a member.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.context import Context

from coalitionkit_contracts import is_ulid
from coalitionkit_edges.a2a.host_port import HostPort

from .errors import CoalitionToolError
from .ports import HostedParticipant, SkillsPort, TokenPort, ViewPort


def utc_now() -> datetime:
    return datetime.now(UTC)


def rfc3339(moment: datetime) -> str:
    """``moment`` as a UTC RFC 3339 string with a ``Z`` offset."""
    return moment.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class Deps:
    """The ports and the clock a server is built from."""

    host: HostPort
    view: ViewPort
    tokens: TokenPort
    clock: Callable[[], datetime] = field(default=utc_now)
    skills: SkillsPort | None = None


class CoalitionMCPServer(MCPServer):
    """An MCPServer that carries its ``Deps``, so tools and resolvers can reach them."""

    deps: Deps

    def __init__(self, deps: Deps, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.deps = deps


def deps_of(ctx: Context) -> Deps:
    server = ctx.mcp_server
    if not isinstance(server, CoalitionMCPServer):
        raise RuntimeError("this context does not belong to a CoalitionMCPServer")
    return server.deps


async def authenticate(ctx: Context) -> HostedParticipant:
    """The participant behind this call's bearer token (``unknown_participant`` when none)."""
    access = get_access_token()
    hosted = None if access is None else await deps_of(ctx).tokens.participant_for(access.token)
    if hosted is None:
        raise CoalitionToolError("unknown_participant", "the access token maps to no participant")
    return hosted


async def authorize(ctx: Context, coalition_id: str) -> HostedParticipant:
    """Authenticate, then require membership of ``coalition_id``.

    A Coalition the participant does not belong to answers ``unknown_participant``, the same
    whether it exists or not.
    """
    hosted = await authenticate(ctx)
    if not is_ulid(coalition_id):
        raise CoalitionToolError("schema_invalid", "coalition_id is not a ULID")
    if not await deps_of(ctx).view.is_member(hosted.participant, coalition_id):
        raise CoalitionToolError("unknown_participant", "not a participant of this Coalition")
    return hosted
