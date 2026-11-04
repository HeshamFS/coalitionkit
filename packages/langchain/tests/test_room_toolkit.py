# SPDX-License-Identifier: Apache-2.0
"""The room's tools for LangChain: only this seat's room, and only the person's answer is signed."""

from __future__ import annotations

from coalitionkit_langchain import RoomToolkit, Seat
from langchain_core.tools import BaseTool

from coalitionkit_mcp.testing_rig import C1, COST, OFFER_TARGET, PLAN, Rig

DECIDE = {"subject": {"kind": "plan", "id": PLAN, "revision": 1}, "choice": PLAN}


def seat_for(rig: Rig, who: str = "p1") -> Seat:
    return Seat(rig.url.removesuffix("/mcp"), C1, who, "member", f"tok-{who}")


def tool(tools: list[BaseTool], name: str) -> BaseTool:
    return next(t for t in tools if t.name == name)


async def test_the_tools_are_the_rooms_and_the_seat_fills_in_its_own_room(rig: Rig) -> None:
    async with RoomToolkit(seat_for(rig, "p2")) as room:
        names = {t.name for t in room.tools}
        offer = tool(room.tools, "make_offer")
        assert "coalition_id" not in offer.args
        said = await offer.ainvoke({"target": OFFER_TARGET, "capacity": 1, "cost": COST})
    assert {"open_asks", "my_view", "make_offer", "decide", "report_done"} <= names
    assert not names & {"join_coalition", "leave_coalition", "list_coalitions"}
    assert "Offer" in said
    sent = rig.host.accepted[-1]
    assert sent["type"] == "coalition.offer" and sent["coalition_id"] == C1


async def test_only_the_persons_answer_is_signed(rig: Rig) -> None:
    asked: list[str] = []

    async def says_no(question: str) -> bool:
        asked.append(question)
        return False

    async with RoomToolkit(seat_for(rig), ask_person=says_no) as room:
        forged = {**DECIDE, "consent": True, "confirmed": True}
        await tool(room.tools, "decide").ainvoke(forged)
    assert rig.host.accepted[-1]["payload"]["consent"] is False
    assert PLAN in asked[0] and "revision 1" in asked[0]


async def test_a_person_who_does_not_answer_signs_nothing(rig: Rig) -> None:
    async def silent(_: str) -> None:
        return None

    async with RoomToolkit(seat_for(rig), ask_person=silent) as room:
        said = await tool(room.tools, "decide").ainvoke(DECIDE)
    assert "did not answer" in said
    assert rig.host.accepted == []


async def test_without_a_way_to_ask_the_agent_is_told_where_the_person_signs(rig: Rig) -> None:
    async with RoomToolkit(seat_for(rig)) as room:
        said = await tool(room.tools, "accept_charter").ainvoke({})
    assert "nothing was signed" in said and "/signin" in said
    assert rig.host.accepted == []
