# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false, reportOptionalMemberAccess=false, reportOptionalIterable=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false
"""The MCP App view: the bundled file, its metadata, and every read tool that links to it."""

from __future__ import annotations

import re
from typing import Any

from coalitionkit_mcp.testing_rig import C1, Rig
from coalitionkit_mcp.view import CSP, MAX_VIEW_BYTES

VIEW = "ui://coalitionkit/surface-v1.html"
APP_MIME = "text/html;profile=mcp-app"


async def test_the_resource_is_the_bundled_view_with_the_app_mime_and_closed_csp(rig: Rig) -> None:
    async with rig.connect("p1") as client:
        result = await client.read_resource(VIEW)
    content = result.contents[0]
    html: str = content.text  # type: ignore[union-attr]
    assert content.mime_type == APP_MIME
    assert content.meta is not None
    assert content.meta["ui"]["csp"] == {}  # the resource names no origin beyond the default
    assert content.meta["ui"]["prefersBorder"] is True
    assert len(html.encode()) < MAX_VIEW_BYTES
    assert "A2uiSurface" in html or "coalitionkit/v0_9" in html  # the catalog is in the file
    policy = re.search(r'http-equiv="Content-Security-Policy"\s+content="([^"]*)"', html)
    assert policy is not None and policy.group(1) == CSP


async def test_the_view_file_asks_for_nothing_outside_itself(rig: Rig) -> None:
    async with rig.connect("p1") as client:
        html: str = (await client.read_resource(VIEW)).contents[0].text  # type: ignore[union-attr]
    assert not re.search(r"<script[^>]*\ssrc=", html, re.I)
    assert not re.search(r"<link\b", html, re.I)
    assert not re.search(r"<(img|iframe|video|audio|source|embed|object)\b[^>]*\ssrc=", html, re.I)
    assert not re.search(r"@import|url\(\s*[\"']?https?:", html, re.I)
    assert C1 not in html  # the Coalition ID travels as tool data, never in the file or its URI


async def test_every_read_tool_the_view_can_draw_links_to_it(rig: Rig) -> None:
    async with rig.connect("p1") as client:
        listed = await client.list_tools()
    linked = {
        t.name for t in listed.tools if ((t.meta or {}).get("ui") or {}).get("resourceUri") == VIEW
    }
    assert linked == {"my_view", "list_coalitions", "pending_questions"}


async def test_my_view_carries_the_viewers_events_in_order_and_readable_text(rig: Rig) -> None:
    async def surface(participant: str, coalition_id: str, device: str) -> dict[str, Any]:
        events = {
            "b": {"type": "coalition.join", "seq": 2, "payload": {}, "hash": "never"},
            "a": {"type": "coalition.charter", "seq": 1, "payload": {"goal": "Goal 1"}},
            "c": {
                "type": "coalition.observe",
                "seq": 3,
                "payload": {"content": "Room  is" + chr(10) + "free"},
            },
        }
        return {"coalition_id": coalition_id, "events": events, "secret_note": "never shown"}

    rig.view.surface = surface
    async with rig.connect("p1") as client:
        result = await client.call_tool("my_view", {"coalition_id": C1, "device": "mcp-app"})
    assert not result.is_error
    data = result.structured_content
    assert [e["seq"] for e in data["surface"]["events"]] == [1, 2, 3]
    assert data["surface"]["events"][0]["payload"] == {"goal": "Goal 1"}
    text = result.content[0].text  # type: ignore[union-attr]
    assert text.splitlines()[0] == "Goal 1" and "Log entries: 3" in text
    # A host that reads only the text still sees a note's own words.
    assert "- #3 coalition.observe: Room is free" in text.splitlines()
    assert "never" not in str(result)  # fields no allowlist names are dropped
    assert (result.meta or {})["ui"]["resourceUri"] == VIEW
