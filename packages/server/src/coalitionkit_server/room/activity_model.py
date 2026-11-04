# SPDX-License-Identifier: Apache-2.0
"""Model calls as tool activity: ``model:brief``, ``model:offer``, ``model:plan`` and the rest.

The engine's one model wrapper (``model.ask``) opens a trace before the call and closes it with
the measured time and what the call cost. The lines say which step the agent is at, never what
the prompt or the reply held.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from coalitionkit_models import Completion

from .activity import record_activity

if TYPE_CHECKING:
    from .engine import RoomEngine

#: The engine's activity verb, to the tool name the room sees.
TOOLS = {
    "reading": "model:needs",
    "asking": "model:brief",
    "offering": "model:offer",
    "explaining": "model:plan",
    "making": "model:result",
    "saying": "model:say",
}
#: Words for a step whose own label speaks to one person ("your agent ..."), seen by everyone.
PUBLIC_WORDS = {
    "model:brief": "choosing what to ask its person",
    "model:say": "deciding where its person's words go",
    "model:plan": "writing its person a line about each plan",
    "model:offer": "choosing offers from its person's answers",
}
AGENTS = {"gardener": "gardener", "steward": "steward"}

Finish = Callable[[str, int, str], Awaitable[None]]


def tool_of(verb: str, role: str, label: str) -> str:
    if verb == "making" and label.startswith("Laying out"):
        return "model:composer"
    return TOOLS.get(verb, f"model:{role}")


def spent(reply: Completion) -> str:
    """``done, 812 tokens, $0.000420`` from the gateway's own metering."""
    tokens = reply.usage.prompt_tokens + reply.usage.completion_tokens
    return f"{reply.model}, {tokens} tokens, ${reply.cost_micro_usd / 1_000_000:.6f}"


async def traced(
    engine: RoomEngine,
    coalition: str,
    role: str,
    verb: str,
    label: str,
    seat: str | None,
    only: str | None,
) -> Finish:
    """Record that a model call started; the returned function records how it ended."""
    tool = tool_of(verb, role, label)
    args = PUBLIC_WORDS.get(tool, label) if only is not None else label
    base: dict[str, Any] = {
        "seat": seat or "host",
        "agent": AGENTS.get(role, "hosted") if seat else AGENTS.get(role, "host"),
        "tool": tool,
        "args": args,
        "refs": [],
    }
    started = await record_activity(
        engine, coalition, {**base, "result": "", "status": "started", "ms": 0}
    )

    async def finish(status: str, ms: int, result: str) -> None:
        await record_activity(
            engine,
            coalition,
            {**base, "status": status, "ms": ms, "result": result},
            start=started.get("event_id"),
        )

    return finish
