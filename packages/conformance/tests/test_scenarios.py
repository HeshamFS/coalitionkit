# SPDX-License-Identifier: Apache-2.0
"""Exercise lifecycle probes with a scripted model behind the real Steward."""

from typing import Any
from unittest.mock import AsyncMock

import pytest
from coalitionkit_conformance.operator import ReferenceOperator
from coalitionkit_conformance.runner import run
from test_server import Running

from coalitionkit_models import ModelGateway
from coalitionkit_models.gateway import Completion, Usage


async def test_scripted_lifecycle(running: Running, monkeypatch: pytest.MonkeyPatch) -> None:
    complete = AsyncMock(
        return_value=Completion(
            "steward",
            "scripted",
            '{"action":"allow","reason":"Allowed","redact":[]}',
            Usage(0, 0),
            0,
        )
    )
    monkeypatch.setattr(ModelGateway, "complete", complete)
    target = running.base + "/.well-known/agent-card.json"
    report: dict[str, Any] = await run(
        target, "host", [], operator=ReferenceOperator(target, "admin-test")
    )
    failures = [t for t in report["tests"] if t["status"] == "fail"]
    assert not failures, "\n".join(f"{t['id']}: {t['reason']}" for t in failures)
    by_id = {t["id"]: t for t in report["tests"]}
    for test_id in ("C-10", "C-11", "C-12", "C-15", "C-16", "C-20"):
        assert by_id[test_id]["status"] == "pass", by_id[test_id]
    for test_id in ("C-03", "C-04", "C-05", "C-21"):
        assert by_id[test_id]["status"] == "not run", by_id[test_id]
    assert complete.await_count > 0
