# SPDX-License-Identifier: Apache-2.0
"""The talk tools: ``say`` one line to the room or to one seat, and ``read_talk``.

A line is a signed ``coalition.say`` from the token's own participant; the host checks who it is
for and the Steward reviews it like any member message. Reading the talk returns only what this
participant's projection holds, plus whether the room is talking now.
"""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.mcpserver.context import Context
from mcp_types import CallToolResult

from .access import authorize, deps_of
from .gateway import send
from .results import ok
from .tools_write import ack

ROOM_IS_TALKING = (
    "The room is talking before it plans: say one useful line with the say tool (a question "
    "to one seat, a trade, a caveat, agreement), or pass by saying nothing."
)


async def say(
    coalition_id: str,
    text: str,
    intent: Literal["ask", "answer", "trade", "caveat", "agree", "disagree"],
    ctx: Context,
    to: str = "room",
    re: str | None = None,
) -> CallToolResult:
    """Say one line (at most 280 characters) to the room, or to one seat by its participant ID.

    ``re`` is the event ID of the line you answer. Never say a private value of your person.
    """
    hosted = await authorize(ctx, coalition_id)
    payload: dict[str, Any] = {"to": to, "text": text, "intent": intent}
    if re is not None:
        payload["re"] = re
    accepted = await send(deps_of(ctx).host, hosted, coalition_id, "coalition.say", payload)
    return ok("say", ack(accepted, to=to, intent=intent), f"Said to {to}.")


async def talk_of(participant: str, coalition_id: str, ctx: Context) -> dict[str, Any]:
    """The talk as this participant may see it: from the view when it knows, else closed."""
    view: Any = deps_of(ctx).view
    reader = getattr(view, "talk", None)
    found: dict[str, Any] | None = await reader(participant, coalition_id) if reader else None
    return found or {"open": False, "round": 0, "rounds": 0, "thread": []}


async def read_talk(coalition_id: str, ctx: Context) -> CallToolResult:
    """Read what the agents have said in this room, and whether the room is talking now."""
    hosted = await authorize(ctx, coalition_id)
    talk = await talk_of(hosted.participant, coalition_id, ctx)
    data: dict[str, Any] = {
        "coalition_id": coalition_id,
        "open": bool(talk.get("open")),
        "round": talk.get("round", 0),
        "rounds": talk.get("rounds", 0),
        "thread": [
            {k: line.get(k) for k in ("id", "seq", "from", "to", "intent", "text", "re", "stage")}
            for line in talk.get("thread", [])
        ],
    }
    if data["open"]:
        data["note"] = ROOM_IS_TALKING

    def text(d: dict[str, Any]) -> str:
        head = "The room is talking now." if d["open"] else "The room is not talking now."
        lines = [f"- {t['from']} to {t['to']} ({t['intent']}): {t['text']}" for t in d["thread"]]
        return "\n".join([head, *lines])

    return ok("read_talk", data, text)
