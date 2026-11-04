# SPDX-License-Identifier: Apache-2.0
"""Outside agents' calls as tool activity: MCP tool calls and inbound A2A messages.

``McpActivity`` is the MCP server's ``ActivityPort``: the server's middleware reports each tool
call and this records it in the room. ``A2aActivity`` stands in front of the host for the A2A
edge: each inbound message is accepted as before, then recorded as ``a2a:<type>`` with its
measured time and its outcome. Neither ever changes what the host accepts or answers.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from ..adapter import Document
from .activity import record_activity, records

if TYPE_CHECKING:
    from ..app import Server


class McpActivity:
    def __init__(self, server: Server) -> None:
        self.server = server

    async def record(
        self, coalition_id: str, activity: dict[str, Any], start: str | None = None
    ) -> str | None:
        engine = self.server.room
        if engine is None:
            return None
        accepted = await record_activity(engine, coalition_id, activity, start=start)
        found = accepted.get("event_id")
        return str(found) if found else None


class A2aActivity:
    """The host port the A2A edge uses, recording each inbound message after it is handled."""

    def __init__(self, server: Server) -> None:
        self.server = server

    async def accept(self, envelope_json: Document, authenticated_sender: str) -> Document:
        began = time.monotonic()
        reply = await self.server.accept(envelope_json, authenticated_sender)
        engine = self.server.room
        coalition = str(envelope_json.get("coalition_id", ""))
        if engine is None or not records(engine, coalition):
            return reply
        kind = str(envelope_json.get("type", "")).removeprefix("coalition.")
        error: Document | None = reply.get("error")
        if isinstance(error, dict):
            status, result, refs = "failed", f"refused: {error.get('code', 'error')}", []
        else:
            receipt: Document = reply.get("receipt") or {}
            payload: Document = receipt.get("payload") or {}
            seq = payload.get("seq")
            status, result = "done", f"accepted at seq {seq}"
            refs = [str(envelope_json.get("event_id", ""))]
        await record_activity(
            engine,
            coalition,
            {
                # A refused message's sender is not proven, so it is not named.
                "seat": str(envelope_json.get("on_behalf_of", "")) if refs else "outside",
                "agent": "a2a",
                "tool": f"a2a:{kind}" if kind.isidentifier() else "a2a:message",
                "args": f"{kind} message",
                "result": result,
                "status": status,
                "ms": round((time.monotonic() - began) * 1000),
                "refs": refs,
            },
        )
        return reply
