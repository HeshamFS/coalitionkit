# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportMissingParameterType=false, reportPrivateUsage=false
"""Offers in a scripted room: closed fields, the person's limits, and a helper's own key."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from room_flow import briefs_open, full_room, offers_by, reply_brief
from room_rig import (
    BRIEF,
    NEEDS,
    RoomModel,
    bearer,
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

from coalitionkit_server.room import RoomEngine


def offers_done(cid: str, engine: RoomEngine) -> None:
    until(lambda: engine.read(cid)["offers_done"], 40, "offers")


def test_rule_offers_follow_the_hours_and_say_what_they_did(tmp_path: Path) -> None:
    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF)) as client:
        room, (a, b) = full_room(client)
        cid, engine = room["coalition_id"], engine_of(client)
        a_id, b_id = a["participant"], b["participant"]
        briefs_open(engine, cid, ["p1", a_id, b_id])
        reply_brief(client, room["owner"]["token"], {"q1": "o1", "q2": 2, "q3": ["s1", "s2"]})
        reply_brief(client, a["token"], {"q1": None, "q2": 0, "q3": None})
        reply_brief(client, b["token"], {"q1": None, "q2": None, "q3": None})
        offers_done(cid, engine)
        mine = offers_by(client, cid, "p1")
        titles = {n["id"]: n["title"] for n in engine.read(cid)["needs"]}
        by_need = {titles[o["payload"]["target"]["id"]]: o["payload"]["cost"] for o in mine}
        # Each offer is its own estimate: quicker and easier for what they chose, slower and
        # harder for the rest, never above the most they would give to one job (2 hours).
        assert by_need == {
            "Find a venue": {"minutes": 45, "money": 0, "effort": "low"},
            "Share the costs": {"minutes": 67, "money": 0, "effort": "high"},
            "Write the invitation": {"minutes": 120, "money": 0, "effort": "high"},
        }
        assert offers_by(client, cid, a_id) == [], "0 hours means no offer"
        starter = offers_by(client, cid, b_id)
        assert [o["payload"]["cost"]["minutes"] for o in starter] == [60, 45, 90]
        assert {o["payload"]["cost"]["effort"] for o in starter} == {"medium"}
        feed_b = " ".join(x["text"] for x in view_of(engine, cid, b_id)["mine"]["feed"])
        assert "starting guesses" in feed_b and len(feed_b) < 100
        feed_a = " ".join(x["text"] for x in view_of(engine, cid, a_id)["mine"]["feed"])
        assert "made no offer" in feed_a and "no hours" in feed_a
        feed_1 = " ".join(x["text"] for x in view_of(engine, cid, "p1")["mine"]["feed"])
        assert "offered on 3 of 3 needs" in feed_1 and "nothing binds you" in feed_1
        closed = {"offer_id", "target", "capacity", "cost", "valid_until"}
        assert all(set(o["payload"]) == closed for o in mine + starter)


def test_model_offers_are_clamped_to_the_persons_limits(tmp_path: Path) -> None:
    def offers(user: str) -> dict[str, Any]:
        ids = [n["id"] for n in json.loads(user)["needs"]]
        return {
            "offers": [
                {"need_id": ids[0], "minutes": 9999, "money": 500, "effort": "high"},
                {"need_id": "not-a-need", "minutes": 10, "money": 0, "effort": "low"},
                {"need_id": ids[1], "minutes": 40, "money": 0, "effort": "low"},
            ],
            "note": "Offered what you can give.",
        }

    model = RoomModel(needs=NEEDS, brief=BRIEF, offers=offers)
    with serve(tmp_path, model) as client:
        room, (a, b) = full_room(client)
        cid, engine = room["coalition_id"], engine_of(client)
        briefs_open(engine, cid, ["p1", a["participant"], b["participant"]])
        reply_brief(client, room["owner"]["token"], {"q1": "o1", "q2": 1, "q3": None})
        for who in (a, b):
            reply_brief(client, who["token"], {"q1": None, "q2": 0, "q3": None})
        offers_done(cid, engine)
        made = [o["payload"]["cost"] for o in offers_by(client, cid, "p1")]
        # 9999 is cut to the most they would give to one job; the other estimate stands; the
        # bare third need is covered with this person's own estimate. Nothing is summed.
        assert [c["minutes"] for c in made[:2]] == [60, 40]
        assert all(c["minutes"] <= 60 for c in made) and len(made) == 3
        assert made[0]["money"] == 0, "no money was given, so none is offered"
        assert offers_by(client, cid, a["participant"]) == []
        feed = [x["text"] for x in view_of(engine, cid, "p1")["mine"]["feed"]]
        assert feed[0].startswith("Your agent offered on 2 of 3 needs")
        done = [
            x
            for x in view_of(engine, cid, "p1")["activity"]
            if x["verb"] == "offering" and x["seat"] == "p1" and x["label"].startswith("Offered on")
        ]
        assert done and done[-1]["source"] == "model"


def test_a_helper_offers_with_its_own_key(tmp_path: Path) -> None:
    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF)) as client:
        room = start_room(client, seats=3)
        cid, engine = room["coalition_id"], engine_of(client)
        sign(client, cid, room["owner"]["token"], "p1")
        member = join(client, room)
        sign(client, cid, member["token"], member["participant"])
        until(lambda: len(events(client, cid, "need")) >= 3, what="needs")
        client.post(
            "/v1/room/begin", json={"helpers": True}, headers=bearer(room["owner"]["token"])
        )
        sign(client, cid, member["token"], member["participant"])
        briefs_open(engine, cid, ["p1", member["participant"]])
        reply_brief(client, room["owner"]["token"], {"q1": None, "q2": None, "q3": None})
        reply_brief(client, member["token"], {"q1": None, "q2": None, "q3": None})
        offers_done(cid, engine)
        helper = offers_by(client, cid, "helper-1")
        assert len(helper) == 1 and helper[0]["payload"]["cost"]["minutes"] == 15
        need = engine.read(cid)["helpers"]["helper-1"]["need_id"]
        assert helper[0]["payload"]["target"]["id"] == need
        assert "helper-1" not in server_of(client).hosts[cid].state.charter["deciders"]


def test_a_slow_offer_call_does_not_hold_up_a_click(tmp_path: Path) -> None:
    model = RoomModel(needs=NEEDS, brief=BRIEF, offers={"offers": [], "note": ""}, offers_delay=6)
    with serve(tmp_path, model) as client:
        room, (a, b) = full_room(client)
        cid, engine = room["coalition_id"], engine_of(client)
        briefs_open(engine, cid, ["p1", a["participant"], b["participant"]])
        for who in (room["owner"], a, b):
            reply_brief(client, who["token"], {"q1": None, "q2": 1, "q3": None})
        until(
            lambda: any("An offer says" in str(c[1][0]["content"]) for c in model.calls),
            what="the slow call",
        )
        started = time.monotonic()
        begin = client.post(
            "/v1/room/begin", json={"helpers": False}, headers=bearer(room["owner"]["token"])
        )
        brief = client.post(
            "/v1/room/brief", json={"question_id": "q1", "skip": True}, headers=bearer(a["token"])
        )
        took = time.monotonic() - started
        assert begin.status_code == 200 and brief.status_code == 409
        assert took < 2.5, f"clicks waited {took:.1f}s behind a model call"
        assert not engine.read(cid)["offers_done"], "the call was still running"


def test_a_need_left_bare_is_covered_inside_the_hours_left(tmp_path: Path) -> None:
    def offers(user: str) -> dict[str, Any]:
        ids = [n["id"] for n in json.loads(user)["needs"]]
        return {
            "offers": [{"need_id": ids[0], "minutes": 30, "money": 0, "effort": "low"}],
            "note": "Offered on the first.",
        }

    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF, offers=offers)) as client:
        room, (a, b) = full_room(client)
        cid, engine = room["coalition_id"], engine_of(client)
        briefs_open(engine, cid, ["p1", a["participant"], b["participant"]])
        reply_brief(client, room["owner"]["token"], {"q1": None, "q2": 2, "q3": None})
        reply_brief(client, a["token"], {"q1": None, "q2": 1, "q3": None})
        reply_brief(client, b["token"], {"q1": None, "q2": 0, "q3": None})
        offers_done(cid, engine)
        titles = {n["id"]: n["title"] for n in engine.read(cid)["needs"]}
        covered = {titles[e["payload"]["target"]["id"]] for e in events(client, cid, "offer")}
        assert covered == set(titles.values()), "every need has an offer"
        assert offers_by(client, cid, b["participant"]) == [], "0 hours is still no offer"
        feed = " ".join(x["text"] for x in view_of(engine, cid, "p1")["mine"]["feed"])
        assert "Nobody had offered on" in feed and "nothing binds you" in feed
