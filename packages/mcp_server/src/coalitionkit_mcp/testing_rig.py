# SPDX-License-Identifier: Apache-2.0
"""Shared test rig: constants, the person-playing answerers and the connected-client helper."""

from __future__ import annotations

import socket
from collections.abc import AsyncGenerator, Callable, Generator
from contextlib import AbstractAsyncContextManager, asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from typing import Any

import httpx2
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from mcp import Client
from mcp.client.session import ClientRequestContext
from mcp.client.streamable_http import streamable_http_client
from mcp_types import ElicitRequestParams, ElicitResult, ErrorData

from coalitionkit_edges.a2a.host_port import FakeHost, HostSigner
from coalitionkit_mcp import Deps, HostedParticipant, create_app
from coalitionkit_mcp.testing import FakeCoalition, FakeTokenPort, FakeViewPort, ServedApp

C1 = "01M4XRC000000G40R40M30E209"
C2 = "01M4XRC1J00000000000000000"
TASK = "01M4XRC2A00000000000000002"
TASK_2 = "01M4XRC2A00000000000000003"
PLAN = "01M4XRC2A00000000000000004"
COMMITMENT = "01M4XRC2A00000000000000006"
OFFER_TARGET = {"kind": "task", "id": TASK}
COST = {"minutes": 30, "money": 100, "effort": "low"}

CHARTER: dict[str, Any] = {
    "goal": "Find two hours next week.",
    "roles": [{"id": "member"}],
    "rules": ["no private data leaves a vault"],
    "deadline": "2026-11-05T12:00:00Z",
    "deciders": ["p1"],
    "revision": 2,
    "created_at": "2026-10-29T08:00:00Z",
}


def hosted(name: str) -> HostedParticipant:
    return HostedParticipant(
        participant=name,
        card_url=f"https://agents.example.org/{name}/card.json",
        agent_key=Ed25519PrivateKey.generate(),
        agent_kid=f"{name}-agent",
        owner_key=Ed25519PrivateKey.generate(),
        owner_kid=f"{name}-owner",
    )


Answerer = Callable[[ElicitRequestParams], ElicitResult | ErrorData]


@dataclass
class Rig:
    url: str
    host: FakeHost
    view: FakeViewPort
    people: dict[str, HostedParticipant]
    asked: list[str] = field(default_factory=lambda: [])

    def connect(
        self, name: str, answer: Answerer | None = None, token: str | None = None
    ) -> AbstractAsyncContextManager[Client]:
        """A client logged in as ``name``; ``answer`` plays the person if given."""

        async def callback(context: ClientRequestContext, params: ElicitRequestParams) -> Any:
            self.asked.append(str(getattr(params, "message", "")))
            assert answer is not None
            return answer(params)

        @asynccontextmanager
        async def open_client() -> AsyncGenerator[Client]:
            headers = {"Authorization": f"Bearer {token or 'tok-' + name}"}
            async with httpx2.AsyncClient(headers=headers) as http:
                client = Client(
                    streamable_http_client(self.url, http_client=http),
                    elicitation_callback=callback if answer is not None else None,
                )
                async with client:
                    yield client

        return open_client()


def yes(_: ElicitRequestParams) -> ElicitResult:
    return ElicitResult(action="accept", content={"consent": True})


def no(_: ElicitRequestParams) -> ElicitResult:
    return ElicitResult(action="accept", content={"consent": False})


class FixtureSkills:
    async def skills(self, participant: str, coalition_id: str) -> list[dict[str, Any]]:
        return [{"name": "guide", "title": "Guide", "text": "# Guide\nWork together."}]


@contextmanager
def served_rig(search: Any = None) -> Generator[Rig]:
    """A served MCP app on a real localhost port with a FakeHost."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = int(probe.getsockname()[1])
    people = {"p1": hosted("p1"), "p2": hosted("p2")}
    tokens = FakeTokenPort()
    for name, person in people.items():
        tokens.add(f"tok-{name}", person)
    view = FakeViewPort()
    view.add(
        C1,
        FakeCoalition(
            goal=CHARTER["goal"],
            charter=dict(CHARTER),
            members={"p1": ["member", "organizer"], "p2": ["member"]},
            revisions={("charter", C1): 2, ("commitment", COMMITMENT): 3, ("plan", PLAN): 1},
            tasks={
                "p2": [
                    {
                        "task_id": TASK,
                        "title": "Book room",
                        "status": "decided",
                        "secret_note": "never shown",
                    }
                ]
            },
            questions={
                "p2": [
                    {
                        "query_id": "q-1",
                        "kind": "feasible",
                        "subject": "room",
                        "secret_note": "never shown",
                    }
                ]
            },
        ),
    )
    view.add(
        C2,
        FakeCoalition(
            goal="Another one",
            charter={**CHARTER, "goal": "Another one"},
            members={"p1": ["member"]},
        ),
    )
    host_key = Ed25519PrivateKey.generate()
    host = FakeHost(HostSigner("https://host.example.org/card.json", host_key, "host-1"))
    app = create_app(
        Deps(host=host, view=view, tokens=tokens, skills=FixtureSkills(), search=search),
        public_url=f"http://127.0.0.1:{port}/mcp",
        issuer_url="http://127.0.0.1:1",
        allowed_hosts=["127.0.0.1:*"],
        allowed_origins=["http://127.0.0.1:*"],
    )
    with ServedApp(app, port) as served:
        yield Rig(served.url, host, view, people)
