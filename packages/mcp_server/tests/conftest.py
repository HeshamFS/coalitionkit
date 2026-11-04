# SPDX-License-Identifier: Apache-2.0
"""The ``rig`` and ``traced`` fixtures: a served MCP app on localhost with a FakeHost."""

from __future__ import annotations

from collections.abc import Generator, Iterator
from typing import Any

import pytest

from coalitionkit_contracts import new_ulid
from coalitionkit_mcp.testing_rig import Rig, served_rig


class FixtureSearch:
    """A host search port: refuses a query holding a digit run, else one result."""

    def __init__(self) -> None:
        self.asked: list[tuple[str, str, str]] = []

    async def web_search(
        self, participant: str, coalition_id: str, query: str
    ) -> dict[str, Any] | None:
        self.asked.append((participant, coalition_id, query))
        if any(ch.isdigit() for ch in query):
            return {"refused": "it holds a street address"}
        row = {"title": "A hall", "url": "https://example.org/hall", "snippet": "Big.", "x": 1}
        return {"results": [row]}


@pytest.fixture
def rig() -> Generator[Rig]:
    with served_rig(search=FixtureSearch()) as made:
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
    with served_rig(activity=recorder) as made:
        yield made, recorder
