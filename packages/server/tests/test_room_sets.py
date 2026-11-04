# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportMissingParameterType=false, reportPrivateUsage=false, reportUnknownParameterType=false
"""A pack's compared sets: asked of every seat, crossed by PSI, only the shared part published."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest
from room_flow import briefs_open, reply_brief
from room_rig import BRIEF, NEEDS, RoomModel, bearer, engine_of, server_of, until, view_of
from sets_rig import pack_room, serve_pack
from test_room_compare import Recording

from coalitionkit_server.adapter import Document
from coalitionkit_server.room import makers, sets

CANARY = "canary-zq7x"  # a word only one seat writes; it must never leave that seat's vault


def published(client: Any, cid: str) -> dict[str, Document]:
    out: dict[str, Document] = {}
    for e in server_of(client).store.read(cid):
        if e["type"] == "coalition.observe" and '"set"' in e["payload"]["content"]:
            body = json.loads(e["payload"]["content"])
            out[body["set"]] = {**body, "by": e["on_behalf_of"], "scope": e["scope"]}
    return out


def test_declared_sets_are_asked_crossed_and_only_the_shared_part_is_published(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[Document] = []

    async def record(activity: Document) -> None:
        seen.append(activity)

    monkeypatch.setattr(sets, "hook", lambda engine, coalition: record)
    steward = Recording()
    model = RoomModel(needs=NEEDS, brief=BRIEF)
    with serve_pack(tmp_path, model) as client:
        room, (a, b) = pack_room(client, steward=steward)
        cid, engine = room["coalition_id"], engine_of(client)
        who = ["p1", a["participant"], b["participant"]]
        briefs_open(engine, cid, who)
        asked = [q["id"] for q in view_of(engine, cid, "p1")["mine"]["brief"]]
        assert asked == ["q1", "q2", "q3", "set-colours", "set-words"], "beside the agent's own"
        reply_brief(
            client,
            room["owner"]["token"],
            {
                "q1": None,
                "q2": 3,
                "q3": ["s1"],
                "set-colours": ["o1", "o2", "o3"],
                "set-words": f"Apple, plum , {CANARY}",
            },
        )
        reply_brief(
            client,
            a["token"],
            {
                "q1": None,
                "q2": 3,
                "q3": ["s1"],
                "set-colours": ["o2", "o3", "o4"],
                "set-words": "PLUM; fig",
            },
        )
        reply_brief(
            client,
            b["token"],
            {
                "q1": None,
                "q2": 3,
                "q3": ["s1"],
                "set-colours": ["o2", "o3", "o5"],
                "set-words": None,
            },
        )
        until(lambda: (engine.read(cid)["compare"] or {}).get("state") == "done", 60, "compare")
        found = published(client, cid)
        assert found["colours"]["values"] == ["blue", "green"]
        assert found["colours"]["compared"] == 3 and "count" not in found["colours"]
        assert found["words"] == {
            "common": 1,
            "set": "words",
            "count": 1,
            "compared": 2,
            "by": "p1",
            "scope": {"audience": "coalition"},
        }, "count mode publishes the number only"
        # The room sees what was published; each person sees their own private count.
        public = view_of(engine, cid, b["participant"])["sets"]
        assert [(s["id"], s["values"], s["count"]) for s in public] == [
            ("colours", ["blue", "green"], 2),
            ("words", None, 1),
        ]
        assert view_of(engine, cid, "p1")["mine"]["sets"] == {"colours": 1, "words": 2}
        assert view_of(engine, cid, a["participant"])["mine"]["sets"] == {"colours": 1, "words": 1}
        assert view_of(engine, cid, b["participant"])["mine"]["sets"] == {"colours": 1}
        # The time comparison still works beside the sets, and planning waits for both.
        assert view_of(engine, cid, "p1")["common"]["slots"] == ["s1"]
        until(lambda: engine.may_plan(cid), what="the room to plan")
        facts = sets.facts(engine, cid, engine.read(cid))
        assert facts["colours"]["values"] == ["blue", "green"] and facts["words"] == {
            "label": "Words in common",
            "mode": "count",
            "count": 1,
        }
        # Every PSI round was reported, with names and counts only.
        assert [(x["tool"], x["status"]) for x in seen] == [
            ("psi:compare", "started"),
            ("psi:compare", "done"),
        ] * 2
        assert seen[1]["result"] == "blue, green" and seen[3]["result"] == "1 in common"
        assert seen[1]["refs"] and seen[1]["ms"] >= 0
        # Private values: never in the log, a projection, the Steward, the room document, the
        # feed of another seat, or an activity line. Count mode keeps even the shared word home.
        server = server_of(client)
        host = server.hosts[cid]
        places = {
            "log": json.dumps(server.store.read(cid)),
            "steward": " ".join(steward.seen),
            "engine row": json.dumps(engine.read(cid)),
            "activities": json.dumps(seen),
        }
        for member in who:
            places[f"projection {member}"] = json.dumps(host.view(member))
            places[f"replay {member}"] = json.dumps(host.replay(member))
            if member != "p1":
                places[f"room {member}"] = json.dumps(view_of(engine, cid, member))
                frames = server.surfaces[cid].state.hub.feed_session(member).start()
                places[f"feed {member}"] = " ".join(f.model_dump_json() for f in frames)
        assert CANARY in json.dumps(engine.vault(cid, "p1")), "positive control: the vault has it"
        for secret in (CANARY, "apple", "plum", "fig"):
            leaks = [name for name, text in places.items() if secret in text.lower()]
            assert not leaks, f"{secret} leaked into {leaks}"
        for one_seat_only in ("red", "yellow", "white"):  # options are public; choices are not
            for name in ("log", "steward", "engine row", "activities"):
                assert f'"{one_seat_only}"' not in places[name], (one_seat_only, name)
        rounds = [e for e in server.store.read(cid) if e["type"] == "coalition.match"]
        assert {e["payload"]["match_id"].split("-m")[0] for e in rounds} >= {"colours", "words"}
        assert all(e["scope"]["audience"] == "participants" for e in rounds)


def test_a_set_waits_for_its_seats_and_publishes_nothing_without_them(tmp_path: Path) -> None:
    with serve_pack(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF)) as client:
        room, (a, b) = pack_room(client)
        cid, engine = room["coalition_id"], engine_of(client)
        briefs_open(engine, cid, ["p1", a["participant"], b["participant"]])
        for person, colours in ((room["owner"], ["o1", "o2"]), (a, ["o2"]), (b, None)):
            reply_brief(
                client,
                person["token"],
                {"q1": None, "q2": 3, "q3": None, "set-colours": colours, "set-words": None},
            )
        until(lambda: (engine.read(cid)["compare"] or {}).get("state") == "done", 60, "compare")
        assert published(client, cid) == {}, "every seated person by default; one skipped"
        state = {s["id"]: s for s in view_of(engine, cid, "p1")["sets"]}
        assert state["colours"]["state"] == "done" and state["colours"]["values"] is None
        assert view_of(engine, cid, "p1")["mine"]["sets"] == {}
        until(lambda: engine.may_plan(cid), what="the room to move on")


def test_a_seat_whose_agent_acts_over_mcp_gives_values_through_its_vault(tmp_path: Path) -> None:
    with serve_pack(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF)) as client:
        room, (a, b) = pack_room(client)
        cid, engine = room["coalition_id"], engine_of(client)
        outside = b["participant"]
        # The seat's own agent acts over MCP: the host stops asking it the brief.
        server_of(client).offered_over_mcp(cid, outside)
        briefs_open(engine, cid, ["p1", a["participant"], outside])
        until(lambda: engine.read(cid)["briefs"][outside]["closed"], what="its brief to close")
        given = client.post(
            "/v1/agent/vault",
            json={"values": {"compare:colours": ["Green", "blue", "not-an-option"]}},
            headers=bearer(b["token"]),
        )
        assert given.status_code == 200, given.text
        assert given.json()["keys"] == ["compare:colours"], "keys only, never the values"
        for person, colours in ((room["owner"], ["o2", "o3"]), (a, ["o2", "o3", "o4"])):
            reply_brief(
                client,
                person["token"],
                {"q1": None, "q2": 3, "q3": None, "set-colours": colours, "set-words": None},
            )
        until(lambda: (engine.read(cid)["compare"] or {}).get("state") == "done", 60, "compare")
        found = published(client, cid)["colours"]
        assert found["values"] == ["blue", "green"] and found["compared"] == 3
        assert view_of(engine, cid, outside)["mine"]["sets"] == {"colours": 0}
        log = json.dumps(server_of(client).store.read(cid))
        assert "not-an-option" not in log and "Green" not in log


def test_a_made_list_keeps_to_the_shared_values(monkeypatch: pytest.MonkeyPatch) -> None:
    replies = [
        makers.ListOut(
            items=[
                makers.Item(label="Paint the door red", who="anyone"),
                makers.Item(label="Bring blue cups", who="anyone"),
            ]
        ),
        makers.ListOut(
            items=[
                makers.Item(label="Paint the door green", who="anyone"),
                makers.Item(label="Bring blue cups", who="anyone"),
            ]
        ),
    ]
    told: list[str] = []

    async def fake_ask(engine, coalition, role, system, user, schema, **kw):
        told.append(user["fix_this"])
        assert user["facts"]["sets"]["colours"]["values"] == ["blue", "green"]
        assert "choose only from its values" in system
        return replies[len(told) - 1]

    monkeypatch.setattr(makers, "ask", fake_ask)
    facts: Document = {
        "goal": "g",
        "need": {"id": "n1", "title": "Things", "kind": "list", "detail": ""},
        "plan": [],
        "common": [],
        "people": [],
        "amount": None,
        "sets": {
            "colours": {
                "label": "Colours",
                "mode": "overlap",
                "values": ["blue", "green"],
                "choose_only_from_these": True,
                "options": ["red", "blue", "green", "yellow", "white"],
            }
        },
    }
    made = asyncio.run(makers.make_data(None, "c", "list", "p1", "n1", facts))  # type: ignore[arg-type]
    assert made is not None and made["items"][0]["label"] == "Paint the door green"
    assert told == ["", "choose only from what everyone shares; leave out red"]
    assert sets.strays("Bredth of reds", facts["sets"]) == [], "whole words only"
