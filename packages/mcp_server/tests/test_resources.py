# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false, reportOptionalMemberAccess=false, reportOptionalIterable=false
"""Resources, the view resource and bearer auth."""

from __future__ import annotations

import json
import re
from typing import Any

import httpx2
import pytest
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.exceptions import MCPError

from coalitionkit_mcp.testing_rig import C1, C2, Rig
from coalitionkit_mcp.view import CSP

VIEW = "ui://coalitionkit/surface-v1.html"


def seed_log(rig: Rig) -> None:
    def event(seq: int, scope: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "seq": seq,
            "event_id": f"e{seq}",
            "type": "coalition.offer",
            "ts": "2026-10-29T08:00:00Z",
            "on_behalf_of": "p1",
            "scope": scope,
            "payload": payload,
            "prev_hash": "a" * 64,
            "hash": "b" * 64,
        }

    rig.view.by_id[C1].events = [
        event(1, {"audience": "coalition"}, {"note": "all see this"}),
        event(2, {"audience": "participants", "participants": ["p1"]}, {"note": "p1 only"}),
        event(3, {"audience": "coalition", "redact": ["payload.window"]},
              {"note": "open", "window": "secret"}),
    ]  # fmt: skip


async def read(rig: Rig, name: str, uri: str) -> dict[str, Any]:
    async with rig.connect(name) as client:
        result = await client.read_resource(uri)
    return json.loads(result.contents[0].text)  # type: ignore[union-attr]


async def test_charter_resource_is_allowlisted(rig: Rig) -> None:
    got = await read(rig, "p2", f"coalition://{C1}/charter")
    assert got["charter"]["goal"] == "Find two hours next week."
    assert "secret_note" not in json.dumps(got)


async def test_my_tasks_resource(rig: Rig) -> None:
    got = await read(rig, "p2", f"coalition://{C1}/my-tasks")
    assert [t["title"] for t in got["tasks"]] == ["Book room"]
    assert "secret_note" not in json.dumps(got)
    assert (await read(rig, "p1", f"coalition://{C1}/my-tasks"))["tasks"] == []


async def test_log_gives_originals_projections_and_stubs(rig: Rig) -> None:
    seed_log(rig)
    got = await read(rig, "p2", f"coalition://{C1}/log?since=0")
    first, hidden, projected = got["entries"]
    assert first["form"] == "original" and first["payload"] == {"note": "all see this"}
    assert set(hidden) == {"seq", "prev_hash", "hash"}  # a stub: no content, no leak
    assert projected["form"] == "projection" and projected["payload"] == {"note": "open"}
    assert projected["redacted"] == ["payload.window"]
    assert "secret_note" not in json.dumps(got) and "leak" not in json.dumps(got)
    own = await read(rig, "p1", f"coalition://{C1}/log?since=0")
    assert own["entries"][1]["payload"] == {"note": "p1 only"}


async def test_log_since_filters_by_sequence(rig: Rig) -> None:
    seed_log(rig)
    got = await read(rig, "p1", f"coalition://{C1}/log?since=2")
    assert [e["seq"] for e in got["entries"]] == [3]
    bare = await read(rig, "p1", f"coalition://{C1}/log")
    assert len(bare["entries"]) == 3


@pytest.mark.parametrize("path", ["charter", "my-tasks", "log?since=0"])
async def test_a_read_outside_the_callers_scope_is_refused(rig: Rig, path: str) -> None:
    async with rig.connect("p2") as client:
        with pytest.raises(MCPError) as caught:
            await client.read_resource(f"coalition://{C2}/{path}")
    assert "unknown_participant" in str(caught.value)


async def test_a_bad_since_is_refused(rig: Rig) -> None:
    async with rig.connect("p1") as client:
        with pytest.raises(MCPError):
            await client.read_resource(f"coalition://{C1}/log?since=-1")


async def test_view_resource_has_the_app_mime_and_a_closed_csp(rig: Rig) -> None:
    async with rig.connect("p1") as client:
        result = await client.read_resource(VIEW)
        listed = await client.list_resources()
    content = result.contents[0]
    assert content.mime_type == "text/html;profile=mcp-app"
    assert content.meta is not None and content.meta["ui"]["csp"] == {}  # no extra origins
    text = content.text  # type: ignore[union-attr]
    policy = re.search(r'http-equiv="Content-Security-Policy"\s+content="([^"]*)"', text)
    assert policy is not None and policy.group(1) == CSP  # closed: nothing but inline style/script
    assert C1 not in text
    assert VIEW in {str(r.uri) for r in listed.resources}


async def test_the_resource_templates_are_listed(rig: Rig) -> None:
    async with rig.connect("p1") as client:
        listed = await client.list_resource_templates()
    templates = {t.uri_template for t in listed.resource_templates}
    assert {"coalition://{id}/charter", "coalition://{id}/my-tasks"} <= templates
    assert any(t.startswith("coalition://{id}/log") for t in templates)


async def test_a_missing_or_unknown_token_is_refused_at_the_door(rig: Rig) -> None:
    for headers in ({}, {"Authorization": "Bearer nope"}):
        async with httpx2.AsyncClient(headers=headers) as http:
            with pytest.raises(BaseException):  # noqa: B017 - connect fails with a group
                async with Client(streamable_http_client(rig.url, http_client=http)) as client:
                    await client.list_tools()


async def test_skills_resource_membership(rig: Rig) -> None:
    assert (await read(rig, "p1", f"coalition://{C1}/skills"))["skills"] == [
        {"name": "guide", "title": "Guide", "text": "# Guide\nWork together."}
    ]
    async with rig.connect("p2") as client:
        with pytest.raises(MCPError, match="unknown_participant"):
            await client.read_resource(f"coalition://{C2}/skills")
