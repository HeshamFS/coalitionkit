# SPDX-License-Identifier: Apache-2.0
"""Take a seat in a room and hand its actions to a LangChain agent as tools.

Everything goes through the room's MCP server, so a seat here can do what any MCP host can and
nothing more. A tool that needs the person asks ``ask_person``. The model never sees that answer
and cannot supply one: no tool argument reaches what is signed. Without ``ask_person`` this client
does not declare that it can ask, and those tools say where the person answers instead.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from types import TracebackType
from typing import Any, Self, cast

import httpx
import httpx2
from langchain_core.tools import BaseTool, StructuredTool
from mcp import Client
from mcp.client.session import ClientRequestContext
from mcp.client.streamable_http import streamable_http_client
from mcp_types import ElicitRequestParams, ElicitResult, ErrorData

#: The tools that need the person's own answer.
CONSENT_TOOLS = frozenset({"accept_charter", "approve_commitment", "decide"})
#: A seat already belongs to one room, so an agent has no use for these.
LEFT_OUT = frozenset({"join_coalition", "leave_coalition", "list_coalitions"})

#: Given the host's own question, the person's yes or no, or None when they do not answer.
AskPerson = Callable[[str], Awaitable[bool | None]]


@dataclass(frozen=True)
class Seat:
    """One seat in one room. Treat ``token`` as a password: keep it away from the model."""

    base_url: str
    coalition_id: str
    participant: str
    role: str
    token: str


async def take_seat(base_url: str, code: str, display_name: str) -> Seat:
    """Take a seat through the room's short code."""
    base = base_url.rstrip("/")
    async with httpx.AsyncClient(timeout=60) as http:
        reply = await http.post(
            f"{base}/v1/door/join",
            headers={"Origin": base},
            json={"code": code, "display_name": display_name},
        )
    reply.raise_for_status()
    body = reply.json()
    return Seat(base, body["coalition_id"], body["participant"], body["role"], body["token"])


def text_of(result: Any) -> str:
    return "\n".join(str(getattr(block, "text", "")) for block in result.content).strip()


class RoomToolkit:
    """An open connection to one seat. Use it with ``async with``, then read ``tools``."""

    def __init__(self, seat: Seat, ask_person: AskPerson | None = None) -> None:
        self.seat = seat
        self.ask_person = ask_person
        self.tools: list[BaseTool] = []
        self._http: httpx2.AsyncClient | None = None
        self._client: Client | None = None

    async def _answer(
        self, context: ClientRequestContext, params: ElicitRequestParams
    ) -> ElicitResult | ErrorData:
        assert self.ask_person is not None
        said = await self.ask_person(str(getattr(params, "message", "")))
        if said is None:
            return ElicitResult(action="decline")
        return ElicitResult(action="accept", content={"consent": said})

    async def __aenter__(self) -> Self:
        headers = {"Authorization": f"Bearer {self.seat.token}"}
        self._http = httpx2.AsyncClient(headers=headers, timeout=180)
        self._client = Client(
            streamable_http_client(f"{self.seat.base_url}/mcp", http_client=self._http),
            elicitation_callback=self._answer if self.ask_person else None,
        )
        await self._client.__aenter__()
        listed = await self._client.list_tools()
        self.tools = [self._tool(t) for t in listed.tools if t.name not in LEFT_OUT]
        return self

    async def __aexit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        if self._client is not None:
            await self._client.__aexit__(kind, error, trace)
        if self._http is not None:
            await self._http.aclose()

    async def call(self, name: str, arguments: dict[str, Any] | None = None) -> str:
        """Call one room tool for this seat. A refusal comes back as text for the agent to read."""
        assert self._client is not None
        sent = {"coalition_id": self.seat.coalition_id, **(arguments or {})}
        try:
            return text_of(await self._client.call_tool(name, sent))
        except Exception as error:
            return f"refused: {error}"

    def _tool(self, tool: Any) -> BaseTool:
        """One MCP tool for LangChain. The seat fills in its own room, so the model need not."""
        schema = dict(cast(dict[str, Any], tool.input_schema))
        schema["properties"] = {
            k: v for k, v in schema.get("properties", {}).items() if k != "coalition_id"
        }
        schema["required"] = [r for r in schema.get("required", []) if r != "coalition_id"]
        schema.setdefault("title", tool.name)
        schema.setdefault("description", tool.description or tool.name)
        name = str(tool.name)

        async def run(**arguments: Any) -> str:
            return await self.call(name, arguments)

        return StructuredTool(
            name=name,
            description=tool.description or name,
            args_schema=schema,
            coroutine=run,
        )
