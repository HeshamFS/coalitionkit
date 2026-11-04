# SPDX-License-Identifier: Apache-2.0
"""The ``rig`` and ``traced`` fixtures: a served MCP app on localhost with a FakeHost."""

from __future__ import annotations

from collections.abc import Generator, Iterator
from typing import Any

import pytest

from coalitionkit_contracts import new_ulid
from coalitionkit_mcp.testing_rig import Rig, served_rig


@pytest.fixture
def rig() -> Generator[Rig]:
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
    with served_rig(activity=recorder) as made:
        yield made, recorder
