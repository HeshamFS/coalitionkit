# SPDX-License-Identifier: Apache-2.0
"""``web_search``: an outside agent searches the web through the host, under the room's policy.

The host screens the query before it leaves (the Steward's deterministic policies, street
addresses, every private value a seat holds) and refuses it with ``steward_blocked`` when one
matches. Results carry only a title, an http(s) URL and a snippet. The search is shown to the
room like any agent's search.
"""

from __future__ import annotations

from typing import Any, cast

from mcp.server.mcpserver.context import Context
from mcp_types import CallToolResult

from .access import authorize, deps_of
from .errors import CoalitionToolError
from .results import ok

QUERY_MAX = 200


async def web_search(coalition_id: str, query: str, ctx: Context) -> CallToolResult:
    """Search the web through the host. Use public words only: never a private detail,
    a contact detail or a street address (the host refuses such a query)."""
    hosted = await authorize(ctx, coalition_id)
    words = " ".join(query.split())
    if not words or len(words) > QUERY_MAX:
        raise CoalitionToolError("schema_invalid", f"query must be 1 to {QUERY_MAX} characters")
    port = deps_of(ctx).search
    found = None if port is None else await port.web_search(hosted.participant, coalition_id, words)
    if found is None:
        raise CoalitionToolError("not_authorized", "web search is off on this host")
    if found.get("refused"):
        raise CoalitionToolError("steward_blocked", str(found["refused"]))
    raw: Any = found.get("results")
    results: list[Any] = list(cast(list[Any], raw)) if isinstance(raw, list) else []
    data = {"coalition_id": coalition_id, "query": words, "results": results}
    return ok("web_search", data, f"{len(results)} web result(s) for: {words}")
