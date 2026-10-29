# SPDX-License-Identifier: Apache-2.0
"""The MCP server over a real ``CoalitionHost``: a view port, a host port and a client helper."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Any, cast

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.exceptions import MCPError

from coalitionkit_contracts import prev_hash
from coalitionkit_edges.a2a.testing import free_port
from coalitionkit_mcp import Deps, HostedParticipant
from coalitionkit_mcp.app import create_app
from coalitionkit_mcp.testing import FakeTokenPort, ServedApp
from coalitionkit_runtime import Acknowledgement, AuthenticatedSender, CoalitionHost

from .arena import Participant

Document = dict[str, Any]
Sink = Callable[[str, str, str, object], None]


class HostBackedPorts:
    """Both MCP ports over one host. Reads go through the host's own delivery functions."""

    def __init__(self, host: CoalitionHost, people: dict[str, Participant], sink: Sink) -> None:
        self.host, self.people, self.sink = host, people, sink
        self.by_card = {p.auth.card_url: p.auth for p in people.values()}

    # -- HostPort ----------------------------------------------------------------------------

    async def accept(self, envelope_json: Document, authenticated_sender: str) -> Document:
        sender: AuthenticatedSender | None = self.by_card.get(authenticated_sender)
        if sender is None:
            return {"error": {"code": "unknown_participant", "detail": {}, "ref": "0" * 26}}
        reply = await asyncio.to_thread(self.host.accept, envelope_json, sender)
        if isinstance(reply, Acknowledgement):
            who = sender.participant
            self.sink("ack", who, "mcp write", reply.accepted)
            self.sink("receipt", who, "mcp write", reply.receipt)
            return {"accepted": reply.accepted, "receipt": reply.receipt}
        self.sink("error", sender.participant, "mcp write", reply)
        return {"error": reply["payload"]}

    # -- ViewPort ----------------------------------------------------------------------------

    async def is_member(self, participant: str, coalition_id: str) -> bool:
        return coalition_id == self.host.coalition_id and participant in self.host.state.members

    def _summary(self) -> Document:
        state = self.host.state
        return {
            "coalition_id": self.host.coalition_id,
            "goal": state.charter.get("goal", ""),
            "roles": ["member"],
            "status": state.stage,
            "revision": state.charter.get("revision"),
        }

    async def coalitions(self, participant: str) -> list[Document]:
        member = await self.is_member(participant, self.host.coalition_id)
        return [self._summary()] if member else []

    async def coalition(self, participant: str, coalition_id: str) -> Document | None:
        return self._summary() if await self.is_member(participant, coalition_id) else None

    async def charter(self, participant: str, coalition_id: str) -> Document | None:
        if not await self.is_member(participant, coalition_id):
            return None
        return dict(self.host.state.charter)

    async def my_tasks(self, participant: str, coalition_id: str) -> list[Document]:
        state = self.host.state
        out: list[Document] = []
        for task_id, task in state.tasks.items():
            if task.get("assignee") != participant or not state.visible(
                task["source"], participant
            ):
                continue
            out.append(
                {
                    "task_id": task_id,
                    "title": task.get("description", ""),
                    "status": task["status"],
                    "assignee": participant,
                    "revision": task["revision"],
                }
            )
        return out

    async def log(self, participant: str, coalition_id: str, since: int) -> list[Document]:
        entries: list[Document] = []
        for item in self.host.replay(participant, since):
            if "type" not in item:
                entries.append({**item, "form": "stub"})
            elif item["type"] == "coalition.projection":
                source, payload = item["payload"]["source"], item["payload"]["payload"]
                entries.append(
                    {
                        **source,
                        "payload": payload,
                        "redacted": item["payload"].get("redacted", []),
                        "form": "projection",
                    }
                )
            else:
                entries.append({**item, "hash": prev_hash(item), "form": "original"})
        return entries

    async def pending_questions(self, participant: str, coalition_id: str) -> list[Document]:
        state = self.host.state
        return [
            {k: query[k] for k in ("query_id", "kind", "subject") if k in query}
            for query in state.queries.values()
            if not query["answered"] and state.visible(query["event"], participant)
        ]

    async def surface(self, participant: str, coalition_id: str, device: str) -> Document:
        summary = self._summary()
        return {
            "title": summary["goal"],
            "status": summary["status"],
            "charter_revision": summary["revision"],
            "tasks": await self.my_tasks(participant, coalition_id),
            "questions": await self.pending_questions(participant, coalition_id),
        }

    async def subject_revision(
        self, participant: str, coalition_id: str, kind: str, subject_id: str
    ) -> int | None:
        found = self.host.state.subject(kind, subject_id)
        return cast("int | None", found.get("revision")) if found else None


class McpRun:
    """A served MCP app for one Coalition, and clients logged in as its members."""

    def __init__(self, ports: HostBackedPorts, tokens: dict[str, str]) -> None:
        self.ports, self.tokens = ports, tokens
        self.token_port = FakeTokenPort()
        for name, person in ports.people.items():
            self.token_port.add(
                tokens[name],
                HostedParticipant(
                    participant=name,
                    card_url=person.auth.card_url,
                    agent_key=person.agent,
                    agent_kid=name,
                    owner_key=person.owner,
                    owner_kid=name + "-owner",
                ),
            )
        self.url = ""

    def serve(self) -> ServedApp:
        port = free_port()
        app = create_app(
            Deps(host=self.ports, view=self.ports, tokens=self.token_port),  # pyright: ignore[reportArgumentType]
            public_url=f"http://127.0.0.1:{port}/mcp",
            issuer_url="http://127.0.0.1:1",
            allowed_hosts=["127.0.0.1:*"],
            allowed_origins=["http://127.0.0.1:*"],
        )
        served = ServedApp(app, port)
        self.url = served.url
        return served

    @asynccontextmanager
    async def session(self, name: str, token: str | None = None) -> AsyncGenerator[McpSession]:
        """A connected client logged in as ``name`` (or as whoever ``token`` belongs to)."""
        headers = {"Authorization": f"Bearer {token or self.tokens[name]}"}
        async with (
            httpx2.AsyncClient(headers=headers) as http,
            Client(streamable_http_client(self.url, http_client=http)) as client,
        ):
            yield McpSession(client)


class McpSession:
    """One logged-in client. Every reply is flattened to the text a model would be handed."""

    def __init__(self, client: Client) -> None:
        self.client = client

    async def call(self, tool: str, args: Document) -> str:
        try:
            result = await self.client.call_tool(tool, args)
        except (MCPError, httpx2.HTTPError, ExceptionGroup) as exc:
            return f"{type(exc).__name__}: {exc}"
        parts = [getattr(block, "text", "") for block in result.content]
        return "\n".join([*parts, json.dumps(result.structured_content, sort_keys=True)])

    async def read(self, uri: str) -> str:
        try:
            result = await self.client.read_resource(uri)
        except (MCPError, httpx2.HTTPError, ExceptionGroup) as exc:
            return f"{type(exc).__name__}: {exc}"
        return "\n".join(getattr(item, "text", "") for item in result.contents)
