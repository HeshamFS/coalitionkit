# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false, reportOptionalMemberAccess=false, reportOptionalIterable=false
"""Every tool's happy path against FakeHost, result shapes, and token isolation."""

from __future__ import annotations

from typing import Any

from coalitionkit_contracts import (
    jwk_to_public_key,
    verify_envelope,
    verify_owner_proof,
)
from coalitionkit_mcp.testing_rig import C1, C2, COMMITMENT, COST, OFFER_TARGET, TASK, Rig

TOOLS = {
    "list_coalitions", "join_coalition", "my_view", "open_asks", "pending_questions",
    "answer_question",
    "make_offer", "decide", "approve_commitment", "report_done", "leave_coalition", "commit",
    "report_ripple", "accept_charter", "web_search", "say", "read_talk",
}  # fmt: skip


def last(rig: Rig) -> dict[str, Any]:
    return rig.host.accepted[-1]


async def test_lists_exactly_the_spec_tools(rig: Rig) -> None:
    async with rig.connect("p1") as client:
        listed = await client.list_tools()
    assert {t.name for t in listed.tools} == TOOLS


async def test_list_coalitions_is_scoped_and_allowlisted(rig: Rig) -> None:
    async with rig.connect("p1") as client:
        result = await client.call_tool("list_coalitions", {})
    assert not result.is_error
    got = result.structured_content or {}
    assert {c["coalition_id"] for c in got["coalitions"]} == {C1, C2}
    assert "secret_note" not in str(result)
    assert C1 in result.content[0].text  # type: ignore[union-attr]


async def test_join_sends_a_signed_join_with_a_valid_owner_proof(rig: Rig) -> None:
    async with rig.connect("p2") as client:
        result = await client.call_tool("join_coalition", {"invite": C1, "roles": ["member"]})
    assert not result.is_error
    sent = last(rig)
    assert sent["type"] == "coalition.join" and sent["on_behalf_of"] == "p2"
    person = rig.people["p2"]
    verify_envelope(sent, person.agent_key.public_key())
    key = verify_owner_proof(sent, agent_public_key=person.agent_key.public_key())
    assert key.public_bytes_raw() == person.owner_key.public_key().public_bytes_raw()
    assert jwk_to_public_key(sent["payload"]["owner_key"])
    got = result.structured_content or {}
    assert got["granted_roles"] == ["member"] and got["charter"]["revision"] == 2
    assert "secret_note" not in str(got)


async def test_join_accepts_an_invite_link(rig: Rig) -> None:
    link = f"https://coalitions.example.org/join/{C1}?x=1"
    async with rig.connect("p1") as client:
        result = await client.call_tool("join_coalition", {"invite": link, "roles": ["member"]})
    assert not result.is_error and last(rig)["coalition_id"] == C1


async def test_my_view_attaches_the_view_and_readable_text(rig: Rig) -> None:
    async with rig.connect("p2") as client:
        result = await client.call_tool("my_view", {"coalition_id": C1, "device": "web"})
        listed = await client.list_tools()
    assert not result.is_error
    assert "Book room" in result.content[0].text  # type: ignore[union-attr]
    assert (result.meta or {})["ui"]["resourceUri"] == "ui://coalitionkit/surface-v1.html"
    tool = next(t for t in listed.tools if t.name == "my_view")
    assert (tool.meta or {})["ui"]["resourceUri"] == "ui://coalitionkit/surface-v1.html"
    assert "secret_note" not in str(result)
    assert (result.structured_content or {})["coalition_id"] == C1


async def test_pending_questions_and_answer(rig: Rig) -> None:
    async with rig.connect("p2") as client:
        asked = await client.call_tool("pending_questions", {"coalition_id": C1})
        done = await client.call_tool(
            "answer_question", {"coalition_id": C1, "query_id": "q-1", "result": "yes"}
        )
        cost = await client.call_tool(
            "answer_question", {"coalition_id": C1, "query_id": "q-2", "result": COST}
        )
    assert (asked.structured_content or {})["questions"][0]["query_id"] == "q-1"
    assert "secret_note" not in str(asked)
    assert not done.is_error and not cost.is_error
    assert last(rig)["type"] == "coalition.answer" and last(rig)["payload"]["result"] == COST


async def test_make_offer_returns_the_offer_id(rig: Rig) -> None:
    args = {"coalition_id": C1, "target": OFFER_TARGET, "capacity": 2, "cost": COST}
    async with rig.connect("p2") as client:
        result = await client.call_tool("make_offer", args)
    assert not result.is_error
    got = result.structured_content or {}
    assert got["offer_id"] == last(rig)["payload"]["offer_id"]
    assert last(rig)["type"] == "coalition.offer"


async def test_commit_create_then_withdraw(rig: Rig) -> None:
    async with rig.connect("p2") as client:
        made = await client.call_tool(
            "commit", {"coalition_id": C1, "task_id": TASK, "status": "pending"}
        )
        cid = (made.structured_content or {})["commitment_id"]
        gone = await client.call_tool(
            "commit",
            {"coalition_id": C1, "task_id": TASK, "status": "withdrawn", "commitment_id": cid},
        )
        bad = await client.call_tool(
            "commit", {"coalition_id": C1, "task_id": TASK, "status": "withdrawn"}
        )
    assert not made.is_error and not gone.is_error
    assert last(rig)["payload"]["status"] == "withdrawn"
    assert bad.is_error and (bad.structured_content or {})["code"] == "schema_invalid"


async def test_ripple_done_and_leave(rig: Rig) -> None:
    evidence = [{"kind": "photo", "ref": "img-1", "verified_by": "p1"}]
    async with rig.connect("p2") as client:
        ripple = await client.call_tool(
            "report_ripple", {"coalition_id": C1, "change": "room gone", "invalidates": [TASK]}
        )
        done = await client.call_tool(
            "report_done", {"coalition_id": C1, "task_id": TASK, "evidence": evidence}
        )
        left = await client.call_tool("leave_coalition", {"coalition_id": C1})
    assert not (ripple.is_error or done.is_error or left.is_error)
    assert [e["type"] for e in rig.host.accepted] == [
        "coalition.ripple", "coalition.done", "coalition.leave",
    ]  # fmt: skip
    assert (left.structured_content or {})["accepted"] is True


async def test_host_refusal_becomes_an_error_with_its_code(rig: Rig) -> None:
    async with rig.connect("p2") as client:
        bad = await client.call_tool(
            "report_ripple", {"coalition_id": C1, "change": "x", "invalidates": ["not-a-ulid"]}
        )
    assert bad.is_error and (bad.structured_content or {})["code"] == "schema_invalid"
    assert rig.host.calls == []


async def test_a_token_cannot_act_as_another_participant(rig: Rig) -> None:
    # p2 is not in C2: the call fails before the host, and p1's own call still signs as p1.
    async with rig.connect("p2") as client:
        denied = await client.call_tool("leave_coalition", {"coalition_id": C2})
    assert denied.is_error and (denied.structured_content or {})["code"] == "unknown_participant"
    assert rig.host.calls == []
    async with rig.connect("p1") as client:
        await client.call_tool("leave_coalition", {"coalition_id": C2})
    sent, sender = rig.host.calls[-1]
    assert sent["on_behalf_of"] == "p1" and sender == rig.people["p1"].card_url
    verify_envelope(sent, rig.people["p1"].agent_key.public_key())


async def test_every_tool_refuses_a_foreign_coalition(rig: Rig) -> None:
    calls: dict[str, dict[str, Any]] = {
        "my_view": {},
        "open_asks": {},
        "pending_questions": {},
        "answer_question": {"query_id": "q", "result": "no"},
        "make_offer": {"target": OFFER_TARGET, "capacity": 1, "cost": COST},
        "commit": {"task_id": TASK, "status": "pending"},
        "report_ripple": {"change": "x", "invalidates": []},
        "report_done": {"task_id": TASK, "evidence": []},
        "leave_coalition": {},
        "say": {"text": "hello", "intent": "ask"},
        "read_talk": {},
    }
    async with rig.connect("p2") as client:
        for name, args in calls.items():
            result = await client.call_tool(name, {"coalition_id": C2, **args})
            assert result.is_error, name
            assert (result.structured_content or {})["code"] == "unknown_participant", name
    assert rig.host.calls == []
    assert COMMITMENT  # imported for the consent tests' sibling module


async def test_say_signs_one_line_as_the_token_participant(rig: Rig) -> None:
    async with rig.connect("p1") as client:
        result = await client.call_tool(
            "say", {"coalition_id": C1, "text": "Who takes the costs?", "intent": "ask"}
        )
        too_long = await client.call_tool(
            "say", {"coalition_id": C1, "text": "x" * 281, "intent": "ask"}
        )
    assert not result.is_error and (result.structured_content or {})["to"] == "room"
    sent = last(rig)
    assert sent["type"] == "coalition.say" and sent["on_behalf_of"] == "p1"
    assert sent["scope"] == {"audience": "coalition"}
    assert sent["payload"] == {"to": "room", "text": "Who takes the costs?", "intent": "ask"}
    assert too_long.is_error and (too_long.structured_content or {})["code"] == "schema_invalid"


async def test_read_talk_and_open_asks_say_when_the_room_is_talking(rig: Rig) -> None:
    line = {
        "id": "e1",
        "seq": 9,
        "from": "p2",
        "to": "room",
        "intent": "trade",
        "text": "I take the venue.",
        "re": None,
        "stage": "start",
        "secret_note": "no",
    }
    rig.view.by_id[C1].talk = {"open": True, "round": 1, "rounds": 2, "thread": [line]}
    async with rig.connect("p1") as client:
        talk = await client.call_tool("read_talk", {"coalition_id": C1})
        asks = await client.call_tool("open_asks", {"coalition_id": C1})
    got = talk.structured_content or {}
    assert got["open"] is True and got["thread"][0]["text"] == "I take the venue."
    assert "secret_note" not in str(talk)
    assert (asks.structured_content or {})["talk"]["next_call"] == {"tool": "say"}
    assert "The room is talking" in str(asks.content[0])
