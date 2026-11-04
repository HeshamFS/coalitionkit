# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportMissingTypeStubs=false
"""A graph that holds a seat: model, then the person if a call needs them, then the tools.

A consent tool never runs on the model's say-so. The ``person`` node pauses the graph with an
``interrupt`` before anything happens, and only what the caller resumes with is passed on as the
person's answer. Asking and acting are separate nodes because LangGraph runs a paused node again
from its start when it resumes: nothing in ``person`` has a side effect, so no offer goes twice.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated, Any, TypedDict, cast

from coalitionkit_langchain import CONSENT_TOOLS, RoomToolkit, Seat
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import Command, interrupt


class PersonAsked(TypedDict):
    """What an interrupt shows: which call waits for the person's yes or no."""

    tool: str
    arguments: dict[str, Any]


class SeatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    #: The person's answer for each tool call that needs one.
    answers: dict[str, bool]


def _calls(state: SeatState) -> list[dict[str, Any]]:
    last = state["messages"][-1]
    return list(cast(Any, last.tool_calls)) if isinstance(last, AIMessage) else []


class GraphSeat:
    """A seat's connection, with room for one person's answer on its way to the host."""

    def __init__(self, seat: Seat) -> None:
        self._answer: bool | None = None
        self.room = RoomToolkit(seat, ask_person=self._given)

    async def _given(self, _question: str) -> bool | None:
        said, self._answer = self._answer, None
        return said

    async def __aenter__(self) -> GraphSeat:
        await self.room.__aenter__()
        return self

    async def __aexit__(self, *details: Any) -> None:
        await self.room.__aexit__(*details)

    @property
    def tools(self) -> list[BaseTool]:
        return self.room.tools

    async def act(self, name: str, arguments: dict[str, Any], answer: bool | None) -> str:
        """Run one tool. ``answer`` is the person's, and it serves this call alone."""
        self._answer = answer
        try:
            return await self.room.call(name, arguments)
        finally:
            self._answer = None


def seat_graph(
    chat: BaseChatModel,
    seat: GraphSeat,
    *,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
    tools: Sequence[BaseTool] | None = None,
) -> Any:
    """Compile the graph. Run it with a ``thread_id``; resume an interrupt with ``resume(yes)``."""
    bound = chat.bind_tools(list(tools if tools is not None else seat.tools))

    async def model(state: SeatState) -> dict[str, list[BaseMessage]]:
        return {"messages": [await bound.ainvoke(state["messages"])]}

    def person(state: SeatState) -> dict[str, dict[str, bool]]:
        answers = dict(state.get("answers") or {})
        for call in _calls(state):
            if call["name"] in CONSENT_TOOLS:
                asked = PersonAsked(tool=call["name"], arguments=call["args"])
                answers[call["id"]] = interrupt(asked) is True
        return {"answers": answers}

    async def act(state: SeatState) -> dict[str, Any]:
        answers = state.get("answers") or {}
        done: list[BaseMessage] = []
        for call in _calls(state):
            answer = answers.get(call["id"]) if call["name"] in CONSENT_TOOLS else None
            text = await seat.act(call["name"], call["args"], answer)
            done.append(ToolMessage(content=text, tool_call_id=call["id"], name=call["name"]))
        return {"messages": done, "answers": {}}

    def after_model(state: SeatState) -> str:
        calls = _calls(state)
        if not calls:
            return END
        return "person" if any(c["name"] in CONSENT_TOOLS for c in calls) else "act"

    graph = StateGraph(SeatState)
    graph.add_node("model", model)
    graph.add_node("person", person)
    graph.add_node("act", act)
    graph.add_edge(START, "model")
    graph.add_conditional_edges("model", after_model, ["person", "act", END])
    graph.add_edge("person", "act")
    graph.add_edge("act", "model")
    return graph.compile(checkpointer=checkpointer or InMemorySaver())


def resume(yes: bool) -> Command[Any]:
    """What to run the graph with after an interrupt: the person's own answer."""
    return Command(resume=yes)
