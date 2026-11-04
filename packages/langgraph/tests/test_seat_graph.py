# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false
"""A graph as a seat: it pauses before a consent, and resuming sends nothing twice."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Self

from coalitionkit_langchain import Seat
from coalitionkit_langgraph import GraphSeat, seat_graph
from coalitionkit_langgraph.seat import resume
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage

from coalitionkit_mcp.testing_rig import C1, COST, OFFER_TARGET, PLAN, Rig

DECIDE = {"subject": {"kind": "plan", "id": PLAN, "revision": 1}, "choice": PLAN}
OFFER = {"target": OFFER_TARGET, "capacity": 1, "cost": COST}
THREAD = {"configurable": {"thread_id": "seat"}}
START = {"messages": [HumanMessage("Do what is waiting.")], "answers": {}}


class Scripted(GenericFakeChatModel):
    """A chat model that says the next scripted thing, and takes tools as a real one does."""

    def bind_tools(self, tools: Sequence[Any], **_: Any) -> Self:  # type: ignore[override]
        return self


def model_saying(*turns: AIMessage) -> Scripted:
    return Scripted(messages=iter([*turns, AIMessage("Nothing else waits.")]))


def calling(*calls: tuple[str, dict[str, Any]]) -> AIMessage:
    return AIMessage(
        "",
        tool_calls=[
            {"id": f"call-{n}", "name": name, "args": args, "type": "tool_call"}
            for n, (name, args) in enumerate(calls)
        ],
    )


def seat_for(rig: Rig, who: str) -> Seat:
    return Seat(rig.url.removesuffix("/mcp"), C1, who, "member", f"tok-{who}")


def decisions(rig: Rig) -> list[dict[str, Any]]:
    return [e for e in rig.host.accepted if e["type"] == "coalition.decide"]


async def test_the_graph_pauses_before_a_consent_and_signs_only_the_resumed_answer(
    rig: Rig,
) -> None:
    async with GraphSeat(seat_for(rig, "p1")) as seat:
        graph = seat_graph(model_saying(calling(("decide", DECIDE))), seat)
        paused = await graph.ainvoke(START, THREAD)
        assert paused["__interrupt__"][0].value == {"tool": "decide", "arguments": DECIDE}
        assert rig.host.accepted == []  # nothing has happened while it waits
        done = await graph.ainvoke(resume(True), THREAD)
    assert "__interrupt__" not in done
    assert decisions(rig)[-1]["payload"]["consent"] is True


async def test_a_no_is_signed_as_a_no(rig: Rig) -> None:
    async with GraphSeat(seat_for(rig, "p1")) as seat:
        graph = seat_graph(model_saying(calling(("decide", DECIDE))), seat)
        await graph.ainvoke(START, THREAD)
        await graph.ainvoke(resume(False), THREAD)
    assert decisions(rig)[-1]["payload"]["consent"] is False


async def test_a_model_cannot_put_the_answer_in_the_arguments(rig: Rig) -> None:
    forged = {**DECIDE, "consent": True, "confirmed": True}
    async with GraphSeat(seat_for(rig, "p1")) as seat:
        graph = seat_graph(model_saying(calling(("decide", forged))), seat)
        await graph.ainvoke(START, THREAD)
        assert rig.host.accepted == []
        await graph.ainvoke(resume(False), THREAD)
    assert decisions(rig)[-1]["payload"]["consent"] is False


async def test_resuming_does_not_send_an_offer_twice(rig: Rig) -> None:
    turn = calling(("make_offer", OFFER), ("decide", DECIDE))
    async with GraphSeat(seat_for(rig, "p1")) as seat:
        graph = seat_graph(model_saying(turn), seat)
        await graph.ainvoke(START, THREAD)
        assert rig.host.accepted == []
        await graph.ainvoke(resume(True), THREAD)
    offers = [e for e in rig.host.accepted if e["type"] == "coalition.offer"]
    assert len(offers) == 1 and len(decisions(rig)) == 1


async def test_an_answer_serves_one_call_only(rig: Rig) -> None:
    first, second = calling(("decide", DECIDE)), calling(("decide", DECIDE))
    async with GraphSeat(seat_for(rig, "p1")) as seat:
        graph = seat_graph(model_saying(first, second), seat)
        await graph.ainvoke(START, THREAD)
        paused = await graph.ainvoke(resume(True), THREAD)
        assert paused["__interrupt__"][0].value["tool"] == "decide"  # it asks again
        assert len(decisions(rig)) == 1
