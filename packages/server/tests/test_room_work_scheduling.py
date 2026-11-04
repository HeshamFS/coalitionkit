# SPDX-License-Identifier: Apache-2.0
"""A completed background result must not be scheduled from an old room snapshot."""

from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest

from coalitionkit_server.room.work import make_results


@pytest.mark.asyncio
async def test_completed_result_is_not_scheduled_from_a_stale_snapshot() -> None:
    state: Any = SimpleNamespace(
        tasks={"task-1": {"status": "committed", "assignee": "p1"}},
        subjects={
            "commitment-1": {
                "id": "commitment-1",
                "kind": "commitment",
                "tasks": ["task-1"],
                "status": "approved",
            }
        },
    )
    stale: dict[str, Any] = {"made": {}}
    current = {"made": {"task-1": {"commitment": "commitment-1", "result": "result-1"}}}
    engine: Any = SimpleNamespace(
        read=Mock(return_value=current), is_hosted=Mock(return_value=True), spawn=Mock()
    )
    await make_results(engine, "coalition-1", state, stale)
    engine.spawn.assert_not_called()
