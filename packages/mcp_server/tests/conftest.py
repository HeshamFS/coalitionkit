# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false, reportOptionalMemberAccess=false, reportOptionalIterable=false
"""The ``rig`` and ``traced`` fixtures: a served MCP app on localhost with a FakeHost."""

from __future__ import annotations

from collections.abc import Generator, Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coalitionkit_contracts import new_ulid
from coalitionkit_edges.a2a.host_port import FakeHost, HostSigner
from coalitionkit_edges.a2a.testing import free_port
from coalitionkit_mcp import Deps, create_app
from coalitionkit_mcp.testing import FakeCoalition, FakeTokenPort, FakeViewPort, ServedApp
from coalitionkit_mcp.testing_rig import C1, C2, CHARTER, COMMITMENT, PLAN, TASK, Rig, hosted


class FixtureSkills:
    async def skills(self, participant: str, coalition_id: str) -> list[dict[str, Any]]:
        return [{"name": "guide", "title": "Guide", "text": "# Guide\nWork together."}]


@contextmanager
def served_rig(activity: Any = None) -> Generator[Rig]:
    """The served app; ``activity`` is an optional ``ActivityPort`` for its tool calls."""
    port = free_port()
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
        Deps(host=host, view=view, tokens=tokens, skills=FixtureSkills(), activity=activity),
        public_url=f"http://127.0.0.1:{port}/mcp",
        issuer_url="http://127.0.0.1:1",
        allowed_hosts=["127.0.0.1:*"],
        allowed_origins=["http://127.0.0.1:*"],
    )
    with ServedApp(app, port) as served:
        yield Rig(served.url, host, view, people)


@pytest.fixture
def rig() -> Any:
    with served_rig() as made:
        yield made


class Recorder:
    def __init__(self) -> None:
        self.seen: list[tuple[str, dict[str, Any], str | None]] = []

    async def record(
        self, coalition_id: str, activity: dict[str, Any], start: str | None = None
    ) -> str | None:
        ident = new_ulid()
        self.seen.append((coalition_id, {**activity, "id": ident}, start))
        return ident


@pytest.fixture
def traced() -> Iterator[tuple[Rig, Recorder]]:
    """A served app whose tool calls go to a ``Recorder``."""
    recorder = Recorder()
    with served_rig(recorder) as made:
        yield made, recorder
