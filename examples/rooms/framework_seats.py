# SPDX-License-Identifier: Apache-2.0
"""A LangChain agent and a LangGraph graph each hold a seat in one real room.

usage: python examples/rooms/framework_seats.py BASE_URL ROOM_CODE

Open a room with `coalitionkit up`, then run this with its code. Each seat knows the room only from
its tools. Each real model runs on your key: COALITIONKIT_META_API_KEY for the LangChain seat and
COALITIONKIT_BASETEN_API_KEY for the LangGraph one. Here the person says yes to whatever they are
asked, so replace `person` with a real question to a real person.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import sys
import time
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
from coalitionkit_langchain import RoomToolkit, take_seat
from coalitionkit_langgraph import GraphSeat, seat_graph
from coalitionkit_langgraph.seat import resume
from langchain.agents import create_agent
from langchain_core.callbacks import UsageMetadataCallbackHandler
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

SYSTEM = """You are the agent of a person called {name} in a small group room. {name} agreed to \
take part, is free at the weekend, can spend up to 25 euro, and will happily do up to two jobs.

Act only through your tools. Do what is waiting now, then stop:
1. Read my_view and open_asks. The view lists each need with its id.
2. Make one offer with make_offer on each need you can really do. Use the target \
{{"kind": "need", "id": "<need id>"}}, and skip any need you see you already offered on.
3. Answer open_asks with the next_call each one gives. Your person is asked inside the call, and \
only their answer counts. Say yes to one plan only: if the log shows someone already said yes to a \
plan, choose that same plan. If a vote is open, answer that instead, with one option_id.
4. For each task assigned to {name}: if no commitment is pending or approved, call commit with \
status pending. When its commitment is approved, do the work and report it with report_done, with \
evidence of kind "note" that says in under 120 characters what you did.

When a call is refused, read why and do not repeat it. When nothing waits, stop and call no tool."""

TURN = "Do what is waiting now, then stop."
GIVE_UP_SECONDS = 90.0


def chat(model: str, key: str, base_url: str, **options: Any) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        api_key=SecretStr(os.environ[key]),
        base_url=base_url,
        # Hidden reasoning counts against this. Too low a cap ends a reply before its tool call.
        max_completion_tokens=8000,
        max_retries=2,
        timeout=120,
        # langchain-openai caches one async client per process, bound to the first event loop.
        http_async_client=httpx.AsyncClient(timeout=120),
        **options,
    )


Log = Callable[[str], None]


async def person(log: Log, seat: str, asked: Any) -> bool:
    log(f"[{seat}] the person is asked: {str(asked)[:180]} -> yes")
    return True


async def keep_going(
    log: Log,
    seat: str,
    read: Callable[[str], Awaitable[str]],
    turn: Callable[[], Awaitable[None]],
    deadline: float,
) -> None:
    """Wake the agent whenever the room has changed. It stops when the room closes to this seat."""
    seen, last = "", 0.0
    while time.monotonic() < deadline:
        view, asks = await read("my_view"), await read("open_asks")
        if view.startswith("refused") or "not_authorized" in view or "unknown" in view[:40]:
            log(f"[{seat}] the room has closed: {view[:120]}")
            return
        mark = hashlib.sha256((view + asks).encode()).hexdigest()
        waiting = '"asks":[]' not in asks.replace(" ", "")
        if mark != seen or (waiting and time.monotonic() - last > GIVE_UP_SECONDS):
            seen, last = mark, time.monotonic()
            log(f"[{seat}] wakes: {asks.splitlines()[0][:100]}")
            try:
                await turn()
            except Exception as error:
                log(f"[{seat}] the turn failed: {type(error).__name__}: {str(error)[:200]}")
        await asyncio.sleep(6)
    log(f"[{seat}] stopped at the deadline")


async def langchain_seat(base: str, code: str, log: Log, deadline: float, used: Any) -> None:
    seat = await take_seat(base, code, "Rami")
    log(f"[langchain] seat {seat.participant}")

    async def ask(question: str) -> bool:
        return await person(log, "langchain", question)

    async with RoomToolkit(seat, ask_person=ask) as room:
        model = chat(
            "muse-spark-1.3",
            "COALITIONKIT_META_API_KEY",
            "https://api.meta.ai/v1",
            reasoning_effort="low",
        )
        agent = create_agent(model, room.tools, system_prompt=SYSTEM.format(name="Rami"))

        async def turn() -> None:
            config = {"recursion_limit": 30, "callbacks": [used]}
            out = await agent.ainvoke({"messages": [HumanMessage(TURN)]}, config)
            for message in out["messages"]:
                if message.type == "tool":
                    log(f"[langchain] {message.name}: {str(message.content)[:160]}")
            log(f"[langchain] says: {str(out['messages'][-1].content)[:200]}")

        await keep_going(log, "langchain", room.call, turn, deadline)


async def langgraph_seat(base: str, code: str, log: Log, deadline: float, used: Any) -> None:
    seat = await take_seat(base, code, "Noor")
    log(f"[langgraph] seat {seat.participant}")
    async with GraphSeat(seat) as held:
        model = chat(
            "meta-models/muse-spark-open",
            "COALITIONKIT_BASETEN_API_KEY",
            "https://inference.baseten.co/v1",
        )
        graph = seat_graph(model, held)
        system = ("system", SYSTEM.format(name="Noor"))
        turns = 0

        async def turn() -> None:
            nonlocal turns
            turns += 1
            config = {
                "configurable": {"thread_id": f"turn-{turns}"},
                "recursion_limit": 40,
                "callbacks": [used],
            }
            start = {"messages": [system, HumanMessage(TURN)], "answers": {}}
            out = await graph.ainvoke(start, config)
            while "__interrupt__" in out:
                yes = await person(log, "langgraph", out["__interrupt__"][0].value)
                out = await graph.ainvoke(resume(yes), config)
            for message in out["messages"]:
                if message.type == "tool":
                    log(f"[langgraph] {message.name}: {str(message.content)[:160]}")
            log(f"[langgraph] says: {str(out['messages'][-1].content)[:200]}")

        await keep_going(log, "langgraph", lambda n: held.room.call(n), turn, deadline)


async def both_seats(base: str, code: str, log: Log, seconds: float = 1500.0) -> dict[str, Any]:
    """Run both seats until the room closes to them. Returns the tokens each model used."""
    used = UsageMetadataCallbackHandler()
    deadline = time.monotonic() + seconds
    await asyncio.gather(
        langchain_seat(base, code, log, deadline, used),
        langgraph_seat(base, code, log, deadline, used),
    )
    return dict(used.usage_metadata)


if __name__ == "__main__":
    print(asyncio.run(both_seats(sys.argv[1], sys.argv[2], lambda line: print(line, flush=True))))
