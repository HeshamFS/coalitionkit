# SPDX-License-Identifier: Apache-2.0
"""Minted devices at the Table: the seat, its public record and its tool calls.

A device is an agent the Mint made from a phone video and a voice note, proved by its attack
suite and approved by its owner's signature. In a room it sits in a seat of its own, beside the
helpers: a member run by the host that says it is an agent, holds its own keys, signs only its
own asks and is never a decider. The minted MCP process gets none of that. It runs on loopback,
gets no keys, tokens or store access, and the host's member only calls its fixed tools: reads,
and holds whose confirm and cancel carry the owner's signature.

The public record of each device is ``doc["devices"][id]``; the hold's nonce and revision live in
the device seat's own vault. Running processes live in memory in the engine's ``Hub``.
"""

from __future__ import annotations

import logging
import time
import weakref
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..adapter import Document
from ..genesis import enroll_member
from .seats import read_state, sign_charter

if TYPE_CHECKING:
    from coalitionkit_mint.publish import Minted

    from .engine import RoomEngine

LOG = logging.getLogger(__name__)
PREFIX = "device-"
HOLD_KEY = "_room_device_hold"  # in the device seat's own vault: id, nonce, revision of its hold
READINGS_KEPT = 24
STAGES = ("capture", "read", "design", "code", "attack", "publish")

Activity = Callable[[Document], Awaitable[None]]


class DeviceRefused(RuntimeError):
    """The minted server refused a call; the text is its refusal code."""


@dataclass
class Hub:
    """What the room keeps in memory for its devices. Tests swap the model clients."""

    running: dict[tuple[str, str], Minted] = field(default_factory=dict[tuple[str, str], "Minted"])
    gateway: Any = None  # a ModelGateway for the Mint; None means the server's own
    media: Any = None  # a MediaClient; None means one built from the server's model settings
    # Contract 1: the orchestrator wires this to the room's tool-activity recorder.
    on_activity: Activity | None = None


HUBS: weakref.WeakKeyDictionary[RoomEngine, Hub] = weakref.WeakKeyDictionary()


def hub(engine: RoomEngine) -> Hub:
    found = HUBS.get(engine)
    if found is None:
        found = HUBS[engine] = Hub()
    return found


def devices(doc: Document) -> dict[str, Document]:
    found: dict[str, Document] = doc.get("devices") or {}
    return found


def put(engine: RoomEngine, coalition: str, pid: str, **fields: Any) -> None:
    def change(d: Document) -> None:
        d.setdefault("devices", {}).setdefault(pid, {}).update(fields)

    engine.update(coalition, change)


def is_device(doc: Document, who: str) -> bool:
    return bool(doc["helpers"].get(who, {}).get("kind") == "device")


def next_id(doc: Document) -> str:
    taken = set(devices(doc))
    n = 1
    while f"{PREFIX}{n}" in taken:
        n += 1
    return f"{PREFIX}{n}"


async def report(
    engine: RoomEngine,
    coalition: str,
    seat: str,
    tool: str,
    args: str,
    result: str,
    status: str,
    ms: int,
    refs: list[str] | None = None,
) -> None:
    """One activity in the shared shape. Lines never hold a nonce, signature or private value."""
    callback = hub(engine).on_activity
    if callback is None:
        return
    activity: Document = {
        "seat": seat,
        "agent": "device",
        "tool": tool,
        "args": args[:200],
        "result": result[:200],
        "status": status,
        "ms": ms,
        "refs": list(refs or []),
    }
    try:
        await callback(activity)
    except Exception:
        LOG.exception("Recording a device activity failed")


async def call(
    engine: RoomEngine,
    coalition: str,
    pid: str,
    tool: str,
    arguments: Document,
    *,
    shown: str = "",
) -> Document:
    """Call one minted tool through the loopback MCP client and report it as ``mint:<tool>``."""
    minted = hub(engine).running.get((coalition, pid))
    if minted is None:
        raise DeviceRefused("offline")
    started = time.monotonic()
    await report(engine, coalition, pid, f"mint:{tool}", shown, "", "started", 0)
    try:
        async with minted.sandbox.client() as client:
            result = await client.call_tool(tool, arguments)
        if result.is_error:
            text = " ".join(getattr(c, "text", "") for c in result.content).strip()
            raise DeviceRefused(text or "refused")
        data: Document = dict(result.structured_content or {})
    except Exception as exc:
        ms = round((time.monotonic() - started) * 1000)
        await report(engine, coalition, pid, f"mint:{tool}", shown, str(exc)[:120], "failed", ms)
        raise
    ms = round((time.monotonic() - started) * 1000)
    await report(engine, coalition, pid, f"mint:{tool}", shown, summary(tool, data), "done", ms)
    return data


def summary(tool: str, data: Document) -> str:
    if tool == "list_free_slots":
        return f"{len(data.get('slots', []))} free slots"
    if tool in {"hold_slot", "confirm", "cancel"}:
        return f"{data.get('state', '')} {clock(data.get('start'))}-{clock(data.get('end'))}"
    if tool == "alarm":
        return f"{len(data.get('fields', []))} over the limit"
    if tool.startswith("read_"):
        return f"value {data.get('value')}"
    return str(data.get("state", "done"))


def clock(minute: Any) -> str:
    if not isinstance(minute, int):
        return "?"
    return f"{minute // 60:02d}:{minute % 60:02d}"


def serves(doc: Document, name: str, asked: list[str] | None) -> list[str]:
    """The needs that require this device: the ones asked for, else those that name it."""
    ids = {n["id"] for n in doc["needs"]}
    if asked:
        return [i for i in asked if i in ids]
    words = {w for w in name.lower().replace("-", " ").split() if len(w) >= 4}
    return [
        n["id"]
        for n in doc["needs"]
        if words & set(f"{n['title']} {n['detail']}".lower().replace("-", " ").split())
    ]


async def enrol(engine: RoomEngine, coalition: str, pid: str) -> None:
    """Seat an approved device through a one-use invitation, as the room seats a helper."""
    server = engine.server
    entry = devices(engine.read(coalition))[pid]
    state = await read_state(engine, coalition)
    label = str(entry["label"])
    need = entry["needs"][0] if entry["needs"] else None

    def seat(d: Document) -> None:
        d["helpers"].setdefault(pid, {"kind": "device", "need_id": need, "label": label})

    engine.update(coalition, seat)
    if pid not in state.members:
        try:
            await engine.thread(server.registry.hosted_for, coalition, pid)
            redeemed: Document = {"coalition_id": coalition, "participant": pid}
        except ValueError:
            token = await engine.thread(server.registry.issue, coalition, pid)
            redeemed = await engine.thread(
                server.registry.redeem, token, server.ports, None, None, label
            )
        role: Any = state.charter["roles"][0]["id"]
        await engine.guard(enroll_member(server, redeemed, role, surfaces=()))
    await sign_charter(engine, coalition, pid)
    put(engine, coalition, pid, state="seated", seated_at=engine.now())
    engine.note(coalition, "joining", f"{label} took a seat as a minted device", seat=pid)


def devices_of(engine: RoomEngine, coalition: str, viewer: str, doc: Document) -> list[Document]:
    """``room.devices``: what everyone may see of each device, plus who may approve it."""
    names = {n["id"]: n["title"] for n in doc["needs"]}
    shown: list[Document] = []
    for pid, d in devices(doc).items():
        online = (coalition, pid) in hub(engine).running
        shown.append(
            {
                "id": pid,
                "label": d.get("label", pid),
                "template": d.get("template"),
                "state": d.get("state"),
                "health": "live" if online and d.get("state") == "seated" else "offline",
                "owner": d.get("owner"),
                "mine": d.get("owner") == viewer,
                "can_approve": d.get("owner") == viewer and d.get("state") == "approve",
                "stages": d.get("stages", []),
                "error": d.get("error"),
                "tools": d.get("tools", []),
                "needs": [{"id": i, "title": names.get(i, i)} for i in d.get("needs", [])],
                "attacks": d.get("attacks"),
                "manifest": d.get("manifest_hash"),
                "cost_micro_usd": d.get("cost_micro_usd"),
                "elapsed": d.get("elapsed"),
                "fields": d.get("fields", []),
                "reading": d.get("reading"),
                "readings": d.get("readings", []),
                "hold": d.get("hold"),
            }
        )
    return shown
