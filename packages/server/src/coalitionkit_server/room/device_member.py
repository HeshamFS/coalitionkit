# SPDX-License-Identifier: Apache-2.0
"""The host-side member of a minted device seat.

A resource device offers on the needs that require it, and each offer stands on a real hold
taken through the minted ``hold_slot`` tool. When the plan gives the need to the device and its
commitment is approved, the hold is confirmed with the owner's signature: the owner's signed yes
on that plan is the consent, and it is used once. If the plan gives the need to someone else, the
hold is released the same way. A display device publishes what its camera reads as
``coalition.observe`` with source ``device``; when a reading crosses its template's threshold the
device sends a ``ripple`` on the needs that name it. Agents never press a device's buttons: the
minted tools are reads, plus holds.
"""

from __future__ import annotations

import json
import logging
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

from coalitionkit_runtime.lifecycle import State

from ..adapter import Document
from . import results
from .devices import (
    HOLD_KEY,
    READINGS_KEPT,
    DeviceRefused,
    call,
    clock,
    devices,
    hub,
    put,
    report,
)
from .offer_rules import OfferItem
from .offers import seeded, send_offer
from .seats import read_state
from .work import active_commitment, offer_events

if TYPE_CHECKING:
    from .engine import RoomEngine

LOG = logging.getLogger(__name__)


async def advance(engine: RoomEngine, coalition: str) -> None:
    """Each seated device does its next missing part: offer, then confirm or release."""
    doc = engine.read(coalition)
    found = devices(doc)
    if not found or not doc["begun"]:
        return
    state = await read_state(engine, coalition)
    for pid, entry in found.items():
        if entry.get("state") != "seated" or pid not in state.members:
            continue
        try:
            if doc["briefs_done"] and not doc["offers_done"] and pid not in doc["offers"]:
                await offer(engine, coalition, pid, entry, state, doc)
            hold: Document = entry.get("hold") or {}
            if hold.get("state") == "held":
                await settle(engine, coalition, pid, entry, state)
        except DeviceRefused as exc:
            engine.note(coalition, "offering", f"The device refused: {exc}", seat=pid)
            put(engine, coalition, pid, refused=str(exc)[:120])
            if pid not in doc["offers"]:
                engine.update(coalition, lambda d, p=pid: d["offers"].__setitem__(p, {"count": 0}))


async def offer(
    engine: RoomEngine, coalition: str, pid: str, entry: Document, state: State, doc: Document
) -> None:
    """Offer on the first need that requires this resource, standing on a real hold."""
    if not seeded(engine, coalition, state, doc):
        return
    need = next((n for n in entry.get("needs", []) if n in state.tasks), None)
    if entry.get("family") != "resource" or need is None:
        engine.update(coalition, lambda d: d["offers"].__setitem__(pid, {"count": 0}))
        return
    free = await call(engine, coalition, pid, "list_free_slots", {}, shown="")
    slots = free.get("slots", [])
    if not slots:
        engine.note(coalition, "offering", "No free slot to hold, so no offer", seat=pid)
        engine.update(coalition, lambda d: d["offers"].__setitem__(pid, {"count": 0}))
        return
    start, end = int(slots[0]["start"]), int(slots[0]["end"])
    held = await call(
        engine,
        coalition,
        pid,
        "hold_slot",
        {"start": start, "end": end, "prerequisites": []},
        shown=f"{clock(start)}-{clock(end)}",
    )
    engine.vault_put(coalition, pid, HOLD_KEY, {k: held[k] for k in HELD})
    item = OfferItem(need_id=need, minutes=end - start, money=0, effort="low")
    sent = await send_offer(engine, coalition, pid, state, item)
    put(
        engine,
        coalition,
        pid,
        hold={"need": need, "start": clock(start), "end": clock(end), "state": "held"},
    )
    engine.note(
        coalition,
        "offering",
        f"Held {clock(start)}-{clock(end)} and offered it",
        seat=pid,
        need=need,
        event=sent,
    )
    engine.update(coalition, lambda d: d["offers"].__setitem__(pid, {"count": 1 if sent else 0}))


HELD = ("id", "start", "end", "nonce", "revision")


def owner_signature(
    engine: RoomEngine, coalition: str, entry: Document, tool: str, args: Document
) -> str:
    """The owner's own key signs one exact operation on one exact manifest."""
    from coalitionkit_contracts.signing import sign_detached
    from coalitionkit_mint.artifact import consent_payload

    person = engine.server.registry.hosted_for(coalition, str(entry["owner"]))
    payload = consent_payload(str(entry["manifest_hash"]), tool, args)
    return sign_detached(payload, person.owner_key, "owner")


async def settle(
    engine: RoomEngine, coalition: str, pid: str, entry: Document, state: State
) -> None:
    hold = entry["hold"]
    task = state.tasks.get(hold["need"])
    if task is None:
        return
    active = active_commitment(state, hold["need"])
    assignee = task.get("assignee")
    if assignee == pid and active and active["status"] == "approved":
        await confirm(engine, coalition, pid, entry, state, str(active["id"]))
    elif assignee not in (None, pid) and task["status"] in {"decided", "committed"}:
        await signed(engine, coalition, pid, entry, "cancel")
        put(engine, coalition, pid, hold={**hold, "state": "released"})
        engine.note(coalition, "making", "Released its hold; the plan chose another", seat=pid)


async def signed(
    engine: RoomEngine, coalition: str, pid: str, entry: Document, tool: str
) -> Document:
    mine = dict(engine.vault(coalition, pid).get(HOLD_KEY) or {})
    args: Document = {k: mine[k] for k in HELD}
    signature = await engine.thread(owner_signature, engine, coalition, entry, tool, args)
    shown = f"{clock(args['start'])}-{clock(args['end'])}, owner signed"
    done = await call(engine, coalition, pid, tool, {**args, "signature": signature}, shown=shown)
    engine.vault_put(coalition, pid, HOLD_KEY, {k: done[k] for k in HELD if k in done})
    return done


async def confirm(
    engine: RoomEngine, coalition: str, pid: str, entry: Document, state: State, commitment: str
) -> None:
    hold = entry["hold"]
    need = str(hold["need"])
    await signed(engine, coalition, pid, entry, "confirm")
    put(engine, coalition, pid, hold={**hold, "state": "confirmed"})
    doc = engine.read(coalition)
    title = f"{entry['label']}, {hold['start']} to {hold['end']}"
    data: Document = {
        "items": [
            {"title": str(entry["label"]), "start": hold["start"], "end": hold["end"], "where": ""}
        ],
        "steps": [],
    }
    data["items"][0]["where"] = "Held and confirmed on the device"
    detail = next((n["detail"] for n in doc["needs"] if n["id"] == need), "")
    refs = [r for r in [offer_events(state).get((pid, need))] if r]
    content: Document = {
        "result": 1,
        "need_id": need,
        "kind": "schedule",
        "title": title,
        "source": "rules",
        "sources": refs,
        "components": results.fixed_tree("schedule", title, detail, data),
        "data": data,
    }
    sent = await engine.submit(
        coalition,
        pid,
        "observe",
        {"source": "document", "content": json.dumps(content)},
        {"audience": "coalition"},
    )

    def mark(d: Document) -> None:
        d["made"][need] = {
            "commitment": commitment,
            "result": sent["event_id"] if sent else None,
            "held": sent is None,
        }

    engine.update(coalition, mark)
    engine.note(coalition, "making", "Confirmed its hold with the owner's signature", seat=pid)


async def read_frame(
    engine: RoomEngine, coalition: str, who: str, pid: str, frame: bytes
) -> Document:
    """The owner's camera frame of the display: read it, publish it, ripple on a crossing."""
    from coalitionkit_mint.reader import append_frame

    from .device_mint import clients

    entry = devices(engine.read(coalition)).get(pid)
    if entry is None or entry.get("owner") != who:
        raise PermissionError(pid)
    minted = hub(engine).running.get((coalition, pid))
    if entry.get("state") != "seated" or entry.get("family") != "device" or minted is None:
        raise LookupError(pid)
    gateway, media = clients(engine)
    started = time.monotonic()
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "frame.png"
        path.write_bytes(frame)
        accepted = await append_frame(minted.folder, path, media, gateway)
    ms = round((time.monotonic() - started) * 1000)
    await report(engine, coalition, pid, "mint:reader", "one frame", f"{accepted} read", "done", ms)
    fields: list[Document] = entry.get("fields", [])
    previous: list[Document] = entry.get("reading") or []
    before = {str(r["field"]): r for r in previous}
    now: list[Document] = []
    for f in fields:
        got = await call(engine, coalition, pid, f"read_{f['id']}", {}, shown="")
        if got.get("value") is None:
            continue
        value = float(got["value"])
        now.append(
            {
                "field": f["id"],
                "value": value,
                "unit": f["unit"],
                "threshold": f["threshold"],
                "over": value > float(f["threshold"]),
                "t": got.get("observed"),
            }
        )
    alarm = await call(engine, coalition, pid, "alarm", {}, shown="")
    if not now:
        return {"accepted": accepted, "reading": [], "rippled": []}
    sent = await engine.submit(
        coalition,
        pid,
        "observe",
        {"source": "device", "content": json.dumps({"device": pid, "readings": now})},
        {"audience": "coalition"},
    )
    kept = [
        *entry.get("readings", []),
        *({"field": r["field"], "value": r["value"], "t": r["t"]} for r in now),
    ]
    put(
        engine,
        coalition,
        pid,
        reading=now,
        readings=kept[-READINGS_KEPT:],
        alarm=alarm.get("fields", []),
    )
    line = ", ".join(f"{r['value']:g} {r['unit']}" for r in now)
    engine.note(
        coalition, "reading", f"Read {line}", seat=pid, event=sent["event_id"] if sent else None
    )
    crossed = [r for r in now if r["field"] in before and before[r["field"]]["over"] != r["over"]]
    rippled = await ripple(engine, coalition, pid, entry, crossed) if crossed else []
    return {"accepted": accepted, "reading": now, "rippled": rippled}


async def ripple(
    engine: RoomEngine, coalition: str, pid: str, entry: Document, crossed: list[Document]
) -> list[str]:
    """A crossing ripples the needs that name the device, once the room has offers to redo."""
    from . import say

    doc = engine.read(coalition)
    state = await read_state(engine, coalition)
    live = [
        i
        for i in entry.get("needs", [])
        if i in state.tasks and state.tasks[i]["status"] not in {"withdrawn"}
    ]
    if not doc["offers_done"] or not live:
        return []
    r = crossed[0]
    side = "above" if r["over"] else "back under"
    text = (
        f"{entry['label']} reads {r['value']:g} {r['unit']}, {side} its limit of {r['threshold']:g}"
    )
    with say.pause_planning(engine, coalition):
        reply = await say.to_change(engine, coalition, pid, text, live, False, "", state)
    return [] if reply.get("stopped") else live
