# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false, reportOptionalMemberAccess=false
"""``web_search``: through the host's screen, members only, allowlisted results."""

from __future__ import annotations

from coalitionkit_mcp.testing_rig import C1, Rig

NOT_MEMBER = "01M4XRC9Z00000000000000009"


async def test_a_member_searches_through_the_host(rig: Rig) -> None:
    async with rig.connect("p2") as client:
        result = await client.call_tool("web_search", {"coalition_id": C1, "query": " a  hall "})
    assert not result.is_error
    got = result.structured_content or {}
    assert got == {
        "coalition_id": C1,
        "query": "a hall",
        "results": [{"title": "A hall", "url": "https://example.org/hall", "snippet": "Big."}],
    }, "only the allowlisted fields leave"


async def test_a_refused_query_is_steward_blocked(rig: Rig) -> None:
    async with rig.connect("p2") as client:
        result = await client.call_tool(
            "web_search", {"coalition_id": C1, "query": "a hall near 12 Mill Road"}
        )
    assert result.is_error
    assert (result.structured_content or {})["code"] == "steward_blocked"


async def test_only_members_and_sane_queries(rig: Rig) -> None:
    async with rig.connect("p2") as client:
        other = await client.call_tool("web_search", {"coalition_id": NOT_MEMBER, "query": "x"})
        empty = await client.call_tool("web_search", {"coalition_id": C1, "query": "   "})
        long = await client.call_tool("web_search", {"coalition_id": C1, "query": "w " * 150})
    assert (other.structured_content or {})["code"] == "unknown_participant"
    assert (empty.structured_content or {})["code"] == "schema_invalid"
    assert (long.structured_content or {})["code"] == "schema_invalid"
