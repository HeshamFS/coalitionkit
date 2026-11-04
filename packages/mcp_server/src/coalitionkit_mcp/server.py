# SPDX-License-Identifier: Apache-2.0
"""Assembles the MCP server: the tools, three resources, one view, bearer-token auth."""

from __future__ import annotations

from typing import Any

from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.context import CallNext, ServerRequestContext
from mcp_types import ToolAnnotations

from .access import CoalitionMCPServer, Deps
from .activity import ToolActivity
from .errors import split_error_text
from .ports import TokenPort
from .resources import CHARTER_URI, LOG_URI, TASKS_URI, charter, log, my_tasks
from .tools_consent import accept_charter, approve_commitment, decide
from .tools_read import VIEW_URI, list_coalitions, my_view, open_asks, pending_questions
from .tools_search import web_search
from .tools_talk import read_talk, say
from .tools_write import (
    answer_question,
    commit,
    join_coalition,
    leave_coalition,
    make_offer,
    report_done,
    report_ripple,
)
from .view import make_apps

READ = ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=False)
WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=False, open_world_hint=False)
#: Reads the open web through the host; sends nothing to the Coalition.
WEB = ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=True)

PLAIN_WRITES = (
    join_coalition,
    answer_question,
    make_offer,
    commit,
    report_ripple,
    report_done,
    leave_coalition,
    say,
)
CONSENT_WRITES = (decide, approve_commitment, accept_charter)
#: Tools that reach outside the Coalition through the host, under its outbound policy.
WEB_READS = (web_search,)
#: The read tools whose results the view can draw; each links to it through its UI metadata.
VIEW_READS = (list_coalitions, pending_questions, open_asks)
#: Read tools with no view of their own.
PLAIN_READS = (read_talk,)


class PortTokenVerifier:
    """Adapts a TokenPort to the SDK's bearer check. The participant is the token's principal."""

    def __init__(self, tokens: TokenPort) -> None:
        self._tokens = tokens

    async def verify_token(self, token: str) -> AccessToken | None:
        hosted = await self._tokens.participant_for(token)
        if hosted is None:
            return None
        return AccessToken(
            token=token, client_id=hosted.participant, scopes=[], subject=hosted.participant
        )


async def carry_error_code(ctx: ServerRequestContext[Any, Any], call_next: CallNext) -> Any:
    """Give an ``isError`` result that names a ``coalition.error`` code that code as data too.

    Errors raised inside resolvers reach the host as text only; this puts ``{code, detail}`` in
    structured content so every error looks the same. At this layer a result is its wire dict.
    """
    result = await call_next(ctx)
    if ctx.method != "tools/call" or not isinstance(result, dict) or not result.get("isError"):  # pyright: ignore[reportUnknownMemberType]
        return result
    if result.get("structuredContent") is not None:  # pyright: ignore[reportUnknownMemberType]
        return result
    blocks: Any = result.get("content")  # pyright: ignore[reportUnknownMemberType]
    text: Any = blocks[0].get("text") if isinstance(blocks, list) and blocks else None  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
    found = split_error_text(text) if isinstance(text, str) else None
    if found is not None:
        body = {"code": found[0], **({"detail": found[1]} if found[1] else {})}
        return {**result, "structuredContent": body}  # pyright: ignore[reportUnknownVariableType]
    return result


def build_server(deps: Deps, *, public_url: str, issuer_url: str) -> CoalitionMCPServer:
    """The server for ``deps``: ``public_url`` is the MCP endpoint, ``issuer_url`` the issuer."""
    apps = make_apps()
    apps.tool(
        resource_uri=VIEW_URI,
        name="my_view",
        description="Show your live Coalition surface as readable text, with its data attached.",
        annotations=READ,
    )(my_view)
    for read in VIEW_READS:
        apps.tool(resource_uri=VIEW_URI, name=read.__name__, annotations=READ)(read)
    server = CoalitionMCPServer(
        deps,
        name="coalitionkit",
        title="CoalitionKit",
        instructions=(
            "Join and work in a Coalition. Decisions, commitment approvals and charter "
            "acceptances ask the person a question; answer it only for the person."
        ),
        token_verifier=PortTokenVerifier(deps.tokens),
        auth=AuthSettings(
            issuer_url=issuer_url,  # pyright: ignore[reportArgumentType]
            resource_server_url=public_url,  # pyright: ignore[reportArgumentType]
            validate_token_resource=False,
        ),
        extensions=[apps],
        middleware=[
            carry_error_code,
            *([ToolActivity(deps.activity, deps.tokens.participant_for)] if deps.activity else []),
        ],
    )
    for fn in (*PLAIN_WRITES, *CONSENT_WRITES):
        server.add_tool(fn, annotations=WRITE)
    for fn in WEB_READS:
        server.add_tool(fn, annotations=WEB)
    for read in PLAIN_READS:
        server.add_tool(read, annotations=READ)
    server.resource(CHARTER_URI, name="charter", mime_type="application/json")(charter)
    server.resource(TASKS_URI, name="my-tasks", mime_type="application/json")(my_tasks)
    server.resource(LOG_URI, name="log", mime_type="application/json")(log)
    return server
