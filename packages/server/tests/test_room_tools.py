# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false
"""Every tool call is visible: ``coalition.tool`` events, ``room.tools`` and ``seats[].busy``."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path

from room_flow import briefs_open, reply_brief
from room_rig import (
    BRIEF,
    NEEDS,
    RoomModel,
    engine_of,
    events,
    join,
    serve,
    server_of,
    sign,
    start_room,
    until,
    view_of,
)

from coalitionkit_mcp.gateway import build_envelope
from coalitionkit_server.adapter import Document
from coalitionkit_server.room.activity import WITHHELD, record_activity
from coalitionkit_server.room.activity_ports import A2aActivity
from coalitionkit_server.room.view_tools import add_busy, tools_of

CANARY = "canary-quartz-41"
TEXT_BRIEF: Document = {
    "questions": [
        BRIEF["questions"][0],
        BRIEF["questions"][2],
        {
            "ask": "Anything we should know?",
            "why": "Your agent reads it before offering.",
            "kind": "text",
            "options": [],
            "low": 0,
            "high": 0,
            "step": 0,
            "unit": "",
        },
    ]
}


def room_with_real_steward(client, seats: int = 3, joined: int = 2):  # type: ignore[no-untyped-def]
    room = start_room(client, seats=seats, real_steward=True)
    cid = room["coalition_id"]
    sign(client, cid, room["owner"]["token"], "p1")
    members = [join(client, room) for _ in range(joined)]
    for member in members:
        sign(client, cid, member["token"], member["participant"])
    until(lambda: len(events(client, cid, "need")) >= 3, what="needs")
    return room, members


def test_a_room_records_model_psi_and_steward_activity(tmp_path: Path) -> None:
    with serve(tmp_path, RoomModel(needs=NEEDS, brief=TEXT_BRIEF)) as client:
        room, (a, b) = room_with_real_steward(client)
        cid, engine = room["coalition_id"], engine_of(client)
        briefs_open(engine, cid, ["p1", a["participant"], b["participant"]])
        reply_brief(client, room["owner"]["token"], {"q1": None, "q2": ["s1", "s2"], "q3": None})
        reply_brief(client, a["token"], {"q1": None, "q2": ["s2"], "q3": CANARY})
        reply_brief(client, b["token"], {"q1": None, "q2": ["s2", "s3"], "q3": None})
        until(lambda: (engine.read(cid)["compare"] or {}).get("state") == "done", 40, "compare")
        until(
            lambda: any(
                e["payload"]["tool"] == "steward:review" for e in events(client, cid, "tool")
            ),
            what="reviews",
        )
        tools = events(client, cid, "tool")
        names = {e["payload"]["tool"] for e in tools}
        assert {"model:needs", "model:brief", "psi:compare", "steward:review"} <= names
        by_id = {e["event_id"]: e for e in tools}
        for event in tools:
            body = event["payload"]
            assert event["scope"] == {"audience": "coalition"} and event["on_behalf_of"] == "host"
            if body["status"] != "started" and event.get("causation_id"):
                start = by_id[event["causation_id"]]["payload"]
                assert start["status"] == "started"
                assert (start["tool"], start["seat"]) == (body["tool"], body["seat"])
        psi = [e["payload"] for e in tools if e["payload"]["tool"] == "psi:compare"]
        assert [p["status"] for p in psi] == ["started", "done"]
        assert psi[1]["result"] == "1 times in common, published" and psi[1]["seat"] == "p1"
        brief_calls = [e["payload"] for e in tools if e["payload"]["tool"] == "model:brief"]
        assert {p["agent"] for p in brief_calls} == {"hosted"}
        assert all("Your agent" not in p["args"] for p in brief_calls), "said to the room"
        assert "model:say" not in names, "a private note is never traced"
        reviews = [e["payload"] for e in tools if e["payload"]["tool"] == "steward:review"]
        assert all(r["seat"] == "host" and r["agent"] == "steward" for r in reviews)
        assert not any(r["args"].startswith(("match", "query", "answer", "tool")) for r in reviews)
        assert CANARY not in json.dumps(tools), "a private answer reached a tool event"
        view = view_of(engine, cid, "p1")
        shown = view["tools"]
        assert shown and len(shown) <= 50 and all("busy" in s for s in view["seats"])
        assert len(shown) < len(tools), "a start and its finish are one entry"
        assert CANARY not in json.dumps(view_of(engine, cid, b["participant"]))


def test_members_may_not_send_tool_events(tmp_path: Path) -> None:
    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF)) as client:
        room, (a, _) = room_with_real_steward(client)
        cid, server = room["coalition_id"], server_of(client)
        person = server.registry.hosted_for(cid, a["participant"])
        payload = {
            "seat": a["participant"],
            "agent": "hosted",
            "tool": "model:offer",
            "args": "",
            "result": "",
            "status": "done",
            "ms": 1,
            "refs": [],
        }
        envelope = build_envelope(
            person, cid, "coalition.tool", payload, scope={"audience": "coalition"}
        )
        reply = asyncio.run(server.accept(envelope, person.card_url))
        assert reply["error"]["code"] == "not_authorized"


def test_lines_are_checked_before_they_are_recorded(tmp_path: Path) -> None:
    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF)) as client:
        room, _ = room_with_real_steward(client)
        cid, engine = room["coalition_id"], engine_of(client)
        base = {"seat": "p1", "agent": "hosted", "tool": "search:web", "status": "done", "ms": 3}

        async def record() -> list[Document]:
            return [
                await record_activity(
                    engine, cid, {**base, "args": "mail a@b.example", "result": "x"}
                ),
                await record_activity(
                    engine, cid, {**base, "args": "key " + "k" * 48, "result": "word " * 80}
                ),
                await record_activity(
                    engine, cid, {**base, "tool": "Not A Tool", "args": "", "result": ""}
                ),
            ]

        mail, key, bad = asyncio.run(record())
        assert bad == {}, "a malformed activity is dropped, never raised"
        assert mail["payload"]["args"] == WITHHELD and key["payload"]["args"] == WITHHELD
        assert len(key["payload"]["result"]) == 200


def test_an_on_activity_finish_pairs_with_its_start(tmp_path: Path) -> None:
    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF)) as client:
        room, _ = room_with_real_steward(client)
        cid, engine = room["coalition_id"], engine_of(client)
        base = {"seat": "p1", "agent": "hosted", "tool": "search:web", "args": "q", "refs": []}

        async def record() -> tuple[Document, Document]:
            first = await record_activity(
                engine, cid, {**base, "status": "started", "result": "", "ms": 0}
            )
            done = await record_activity(
                engine, cid, {**base, "status": "done", "result": "3", "ms": 9}
            )
            return first, done

        first, done = asyncio.run(record())
        assert done["causation_id"] == first["event_id"]
        state = server_of(client).hosts[cid].state
        mine = [t for t in tools_of(state, "p1") if t["tool"] == "search:web"]
        assert mine == [{**mine[0], "status": "done", "result": "3", "ms": 9}]
        assert mine[0]["id"] == first["event_id"] and mine[0]["ended"] is not None


def test_a_seat_is_busy_while_its_newest_call_runs() -> None:
    at = "2026-11-04T10:00:00+00:00"
    seats = [{"seat": "p1"}, {"seat": "p2"}]
    tools = [
        {"seat": "p1", "tool": "model:offer", "args": "x", "status": "started", "at": at},
        {"seat": "p2", "tool": "model:offer", "args": "y", "status": "done", "at": at},
    ]
    now = datetime.fromisoformat(at).timestamp() + 5
    busy = add_busy(seats, tools, now)
    assert busy[0]["busy"] == {"tool": "model:offer", "args": "x", "since": at}
    assert busy[1]["busy"] is None
    assert add_busy(seats, tools, now + 600)[0]["busy"] is None, "a lost finish expires"


def test_an_inbound_a2a_message_is_recorded(tmp_path: Path) -> None:
    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF)) as client:
        room, (a, _) = room_with_real_steward(client)
        cid, server = room["coalition_id"], server_of(client)
        person = server.registry.hosted_for(cid, a["participant"])
        said = build_envelope(
            person,
            cid,
            "coalition.observe",
            {"source": "chat", "content": "hello room"},
            scope={"audience": "coalition"},
        )
        forged = build_envelope(person, cid, "coalition.leave", {}, scope={"audience": "coalition"})
        forged["sig"] = "x.y.z"
        port = A2aActivity(server)

        async def send() -> None:
            await port.accept(said, person.card_url)
            await port.accept(forged, person.card_url)

        asyncio.run(send())
        found = {e["payload"]["tool"]: e["payload"] for e in events(client, cid, "tool")}
        ok, refused = found["a2a:observe"], found["a2a:leave"]
        assert ok["seat"] == a["participant"] and ok["agent"] == "a2a" and ok["status"] == "done"
        assert ok["refs"] == [said["event_id"]] and ok["result"].startswith("accepted at seq ")
        assert refused["status"] == "failed" and refused["seat"] == "outside"
        assert "hello" not in json.dumps(found), "the message itself is not repeated"
