# SPDX-License-Identifier: Apache-2.0
"""``room.tools`` and ``room.seats[].busy``: the agents' tool calls, read from the log.

Every ``coalition.tool`` event the viewer may see is folded into one entry per call: a start and
its finish (the finish names the start as its ``causation_id``) become one entry whose status is
the finish's. The last 50 calls are shown, newest last. A seat is busy while its newest call has
started and not finished, for at most ``BUSY_S`` seconds (a host that stopped mid-call leaves a
start without a finish).
"""

from __future__ import annotations

from datetime import datetime

from coalitionkit_runtime.lifecycle import State

from ..adapter import Document

KEEP = 50
BUSY_S = 120.0


def tools_of(state: State, viewer: str) -> list[Document]:
    calls: dict[str, Document] = {}
    for event in state.events.values():
        if event["type"] != "coalition.tool" or not state.visible(event, viewer):
            continue
        body = event["payload"]
        start = event.get("causation_id")
        if body["status"] != "started" and start in calls:
            item = calls[start]
            item.update(
                status=body["status"],
                result=body["result"],
                ms=body["ms"],
                ended=event["ts"],
                refs=list(dict.fromkeys([*item["refs"], *body["refs"]])),
            )
            continue
        calls[event["event_id"]] = {
            "id": event["event_id"],
            "at": event["ts"],
            "seq": event["seq"],
            "seat": body["seat"],
            "agent": body["agent"],
            "tool": body["tool"],
            "args": body["args"],
            "result": body["result"],
            "status": body["status"],
            "ms": body["ms"],
            "refs": list(body["refs"]),
            "ended": None if body["status"] == "started" else event["ts"],
        }
    return list(calls.values())[-KEEP:]


def add_busy(seats: list[Document], tools: list[Document], now: float) -> list[Document]:
    """Each seat gets ``busy``: ``{tool, args, since}`` of its newest running call, or None."""
    running: dict[str, Document] = {}
    for item in tools:
        if item["status"] != "started":
            continue
        if now - datetime.fromisoformat(item["at"]).timestamp() <= BUSY_S:
            running[item["seat"]] = {
                "tool": item["tool"],
                "args": item["args"],
                "since": item["at"],
            }
    return [{**seat, "busy": running.get(seat["seat"])} for seat in seats]
