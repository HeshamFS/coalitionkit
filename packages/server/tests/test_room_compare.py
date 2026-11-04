# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportMissingParameterType=false, reportPrivateUsage=false
"""Comparing times without showing them, plans with words, and what must stay private."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from room_flow import briefs_open, full_room, offers_by, reply_brief
from room_rig import (
    BRIEF,
    NEEDS,
    RoomModel,
    engine_of,
    events,
    serve,
    server_of,
    until,
    view_of,
)

from coalitionkit_runtime.steward import FakeSteward, Verdict
from coalitionkit_server.room import compare
from coalitionkit_vault._group import SodiumUnavailable


def test_times_cross_without_showing_the_lists(tmp_path: Path) -> None:
    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF)) as client:
        room, (a, b) = full_room(client)
        cid, engine = room["coalition_id"], engine_of(client)
        briefs_open(engine, cid, ["p1", a["participant"], b["participant"]])
        reply_brief(client, room["owner"]["token"], {"q1": None, "q2": 3, "q3": ["s1", "s2"]})
        reply_brief(client, a["token"], {"q1": None, "q2": 3, "q3": ["s2", "s3"]})
        reply_brief(client, b["token"], {"q1": None, "q2": 3, "q3": None})
        until(lambda: (engine.read(cid)["compare"] or {}).get("state") == "done", 40, "compare")
        common = view_of(engine, cid, "p1")["common"]
        assert common == {"slots": ["s2"], "count_private": 1, "compared": 2}
        assert view_of(engine, cid, a["participant"])["common"]["count_private"] == 1
        assert view_of(engine, cid, b["participant"])["common"]["count_private"] is None, "sat out"
        assert "count_private" not in json.dumps(engine.read(cid)), "never in the public document"
        log = server_of(client).store.read(cid)
        matches = [e for e in log if e["type"] == "coalition.match"]
        assert [m["payload"]["round"] for m in matches] == ["setup", "request", "response"]
        assert {m["on_behalf_of"] for m in matches} == {"p1", a["participant"]}
        queries = [e for e in log if e["type"] == "coalition.query"]
        answers = [e for e in log if e["type"] == "coalition.answer"]
        assert len(queries) == 3 and sorted(x["payload"]["result"] for x in answers) == [
            "no",
            "yes",
            "yes",
        ]
        seen = [
            e
            for e in log
            if e["type"] == "coalition.observe" and "common" in e["payload"]["content"]
        ]
        assert len(seen) == 1 and json.loads(seen[0]["payload"]["content"])["slots"] == ["s2"]
        assert seen[0]["on_behalf_of"] == "p1" and seen[0]["payload"]["source"] == "document"
        flat = json.dumps([*matches, *seen])
        assert '"s1"' not in flat and '"s3"' not in flat
        # The third person never saw the other two's match rounds.
        host = server_of(client).hosts[cid]
        assert not [
            e
            for e in host.view(b["participant"])["events"].values()
            if e["type"] == "coalition.match"
        ]
        steps = [x for x in view_of(engine, cid, "p1")["activity"] if x["verb"] == "comparing"]
        assert len(steps) >= 4


def test_one_person_with_times_is_not_a_crossing(tmp_path: Path) -> None:
    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF)) as client:
        room, (a, b) = full_room(client)
        cid, engine = room["coalition_id"], engine_of(client)
        briefs_open(engine, cid, ["p1", a["participant"], b["participant"]])
        reply_brief(client, room["owner"]["token"], {"q1": None, "q2": 3, "q3": ["s1"]})
        for who in (a, b):
            reply_brief(client, who["token"], {"q1": None, "q2": 3, "q3": None})
        until(lambda: (engine.read(cid)["compare"] or {}).get("state") == "done", 40, "compare")
        assert view_of(engine, cid, "p1")["common"] is None
        log = server_of(client).store.read(cid)
        assert not [e for e in log if e["type"] == "coalition.match"]
        assert not [e for e in log if e["type"] == "coalition.observe"]
        until(lambda: engine.may_plan(cid), what="the room to move on")


def test_plans_come_with_words_and_a_line_for_each_seat(tmp_path: Path) -> None:
    def names(user: str) -> dict[str, Any]:
        plans = json.loads(user)["plans"]
        return {
            "plans": [
                {"plan_id": p["plan_id"], "name": f"Option {i + 1}", "line": "Shared out."}
                for i, p in enumerate(plans)
            ]
        }

    model = RoomModel(needs=NEEDS, brief=BRIEF, names=names)
    with serve(tmp_path, model) as client:
        room, (a, b) = full_room(client)
        cid, engine = room["coalition_id"], engine_of(client)
        briefs_open(engine, cid, ["p1", a["participant"], b["participant"]])
        for who in (room["owner"], a, b):
            reply_brief(client, who["token"], {"q1": None, "q2": 2, "q3": ["s1", "s2"]})
        until(lambda: events(client, cid, "propose"), 60, "plans")
        until(lambda: engine.read(cid)["plan_notes"], 30, "plan names")
        until(lambda: view_of(engine, cid, "p1")["mine"]["for_you"], 30, "for-you lines")
        view = view_of(engine, cid, "p1")
        plan_ids = {
            p["plan_id"] for e in events(client, cid, "propose") for p in e["payload"]["plans"]
        }
        assert set(view["plan_notes"]) == plan_ids
        assert all(
            n["source"] == "model" and n["name"].startswith("Option")
            for n in view["plan_notes"].values()
        )
        assert set(view["mine"]["for_you"]) == plan_ids
        assert all("you" in line.lower() for line in view["mine"]["for_you"].values())
        assert view["lights"] == "day", "a plan waits for this person's yes"
        assert view["phase"] == "decide"
        # Plans are rule-built: every need has an assignee in every plan.
        for event in events(client, cid, "propose"):
            for plan in event["payload"]["plans"]:
                assert len(plan["assignments"]) == 3


def test_a_need_nobody_offered_on_is_said_aloud(tmp_path: Path) -> None:
    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF)) as client:
        room, (a, b) = full_room(client)
        cid, engine = room["coalition_id"], engine_of(client)
        briefs_open(engine, cid, ["p1", a["participant"], b["participant"]])
        for who in (room["owner"], a, b):
            reply_brief(client, who["token"], {"q1": None, "q2": 0, "q3": None})
        until(lambda: engine.read(cid)["gaps_noted"], 40, "the gap to be named")
        view = view_of(engine, cid, "p1")
        assert [n["status"] for n in view["needs"]].count("no offers") == 3
        said = [x for x in view["activity"] if x["label"].startswith("Nobody has offered on")]
        assert said and said[-1]["state"] == "failed" and "Share the costs" in said[-1]["label"]
        import time

        time.sleep(3.5)
        assert not events(client, cid, "propose"), "a plan cannot cover a need nobody offered on"


SECRET = "private-sentinel-text-answer"
BRIEF3 = {
    "questions": [
        {**BRIEF["questions"][1]},
        {**BRIEF["questions"][2]},
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


class Recording(FakeSteward):
    """A Steward that keeps every envelope it was shown."""

    def __init__(self) -> None:
        super().__init__(Verdict())
        self.seen: list[str] = []

    def review(self, envelope, *, context):
        self.seen.append(json.dumps(envelope))
        return super().review(envelope, context=context)


def test_a_private_answer_never_reaches_anything_public(tmp_path: Path) -> None:
    def offers(user: str) -> dict[str, Any]:
        data = json.loads(user)
        ids = [n["id"] for n in data["needs"]]
        return {
            "offers": [{"need_id": i, "minutes": 20, "money": 0, "effort": "low"} for i in ids],
            "note": f"You told me: {SECRET}." if SECRET in user else "Done.",
        }

    def foryou(user: str) -> dict[str, Any]:
        plans = json.loads(user)["plans"]
        return {
            "plans": [
                {
                    "plan_id": p["plan_id"],
                    "line": (f"You said {SECRET}, so you fit." if SECRET in user else "You fit."),
                }
                for p in plans
            ]
        }

    model = RoomModel(needs=NEEDS, brief=BRIEF3, offers=offers, foryou=foryou)
    steward = Recording()
    with serve(tmp_path, model) as client:
        room, (a, b) = full_room(client, steward=steward)
        cid, engine = room["coalition_id"], engine_of(client)
        server = server_of(client)
        who = ["p1", a["participant"], b["participant"]]
        briefs_open(engine, cid, who)
        reply_brief(client, a["token"], {"q1": 3, "q2": ["s1"], "q3": SECRET})
        for other in (room["owner"], b):
            reply_brief(client, other["token"], {"q1": 3, "q2": ["s1"], "q3": "nothing special"})
        until(lambda: events(client, cid, "propose"), 60, "plans")
        until(lambda: view_of(engine, cid, a["participant"])["mine"]["for_you"], 30, "for you")
        # The person's own side holds it: the feed note, the line for them.
        mine = json.dumps(view_of(engine, cid, a["participant"])["mine"])
        assert SECRET in mine, "positive control: the owner of the answer sees it"
        host = server.hosts[cid]
        with server.store.transaction(cid) as tx:
            stored = json.dumps(tx.execute("SELECT doc FROM room_engine").fetchall())
        public = {
            "log": json.dumps(server.store.read(cid)),
            "steward": " ".join(steward.seen),
            "engine row": json.dumps(engine.read(cid)),
            "stored row": stored,
        }
        for member in who:
            public[f"projection {member}"] = json.dumps(host.view(member))
            public[f"replay {member}"] = json.dumps(host.replay(member))
            if member != a["participant"]:
                public[f"room {member}"] = json.dumps(view_of(engine, cid, member))
                hub = server.surfaces[cid].state.hub
                frames = hub.feed_session(member).start()
                public[f"feed {member}"] = " ".join(f.model_dump_json() for f in frames)
        public["gardener prompts"] = json.dumps([c for c in model.calls if c[0] == "gardener"])
        leaks = [name for name, text in public.items() if SECRET in text]
        assert not leaks, f"the private answer leaked into: {leaks}"
        # Offers carry numbers and ids only.
        for offer in offers_by(client, cid, a["participant"]):
            assert set(offer["payload"]) == {
                "offer_id",
                "target",
                "capacity",
                "cost",
                "valid_until",
            }


def test_the_gate_flow_with_a_helper_reaches_plans(tmp_path: Path) -> None:
    from room_rig import bearer, join, sign, start_room
    from test_room_live import answers_for

    def offers(user: str) -> dict[str, Any]:
        ids = [n["id"] for n in json.loads(user)["needs"]]
        return {
            "offers": [{"need_id": i, "minutes": 30, "money": 0, "effort": "low"} for i in ids],
            "note": "Offered a little on each.",
        }

    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF, offers=offers)) as client:
        room = start_room(client, seats=3)
        cid, engine = room["coalition_id"], engine_of(client)
        member = join(client, room)
        sign(client, cid, room["owner"]["token"], "p1")
        sign(client, cid, member["token"], member["participant"])
        until(lambda: len(events(client, cid, "need")) >= 3, what="needs")
        begun = client.post(
            "/v1/room/begin", json={"helpers": True}, headers=bearer(room["owner"]["token"])
        )
        assert begun.status_code == 200
        sign(client, cid, member["token"], member["participant"])
        who = ["p1", member["participant"]]
        briefs_open(engine, cid, who)
        slots = [s["id"] for s in engine.read(cid)["slots"]]
        for shift, (person, token) in enumerate(
            zip(who, (room["owner"]["token"], member["token"]), strict=True)
        ):
            questions = view_of(engine, cid, person)["mine"]["brief"]
            for question, value in answers_for(questions, slots, shift).items():
                reply = client.post(
                    "/v1/room/brief",
                    json={"question_id": question, "value": value},
                    headers=bearer(token),
                )
                assert reply.status_code == 200, (question, value, reply.text)
        until(lambda: events(client, cid, "propose"), 60, "plans")
        until(lambda: engine.read(cid)["plan_notes"], 30, "plan names")
        assert view_of(engine, cid, "p1")["common"]["slots"] == ["s2", "s3"]
        assert "helper-1" in {o["on_behalf_of"] for o in events(client, cid, "offer")}


def test_a_host_without_the_psi_library_moves_on_and_says_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def missing(*args: Any, **kwargs: Any) -> Any:
        raise SodiumUnavailable("Private set intersection requires coalitionkit[psi]")

    monkeypatch.setattr(compare, "exchange", missing)
    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF)) as client:
        room, (a, b) = full_room(client)
        cid, engine = room["coalition_id"], engine_of(client)
        briefs_open(engine, cid, ["p1", a["participant"], b["participant"]])
        reply_brief(client, room["owner"]["token"], {"q1": None, "q2": 3, "q3": ["s1", "s2"]})
        reply_brief(client, a["token"], {"q1": None, "q2": 3, "q3": ["s2", "s3"]})
        reply_brief(client, b["token"], {"q1": None, "q2": 3, "q3": None})
        until(lambda: (engine.read(cid)["compare"] or {}).get("state") == "done", 40, "compare")
        labels = [a["label"] for a in view_of(engine, cid, "p1")["activity"]]
        assert compare.NO_PSI in labels
        assert engine.may_plan(cid), "the room goes on to plans"
