# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false
"""The Talk stage: agents say lines to each other before plans, and revise their own offers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from room_flow import briefs_open, full_room, offers_by, reply_brief
from room_rig import BRIEF, NEEDS, RoomModel, bearer, engine_of, events, serve, until, view_of

from coalitionkit_server.room.talk_rules import (
    TalkReply,
    checked,
    leaked,
    private_values,
    whispered,
)

PASS: dict[str, Any] = {
    "speak": False,
    "to": "room",
    "intent": "agree",
    "text": "",
    "re": 0,
    "revise": [],
}


def scripted(lines: dict[tuple[str, int], dict[str, Any]]):
    """A talk model: what each seat (by its label) says in each round; everyone else passes."""

    def reply(user: str) -> dict[str, Any]:
        data = json.loads(user)
        line = lines.get((data["you"], data["round"]))
        if line is None:
            return PASS
        out = {**PASS, "speak": True, **line}
        if out["revise"] == ["first"]:
            out["revise"] = [data["needs"][0]["id"]]
        if out["to"] == "other":
            out["to"] = data["seats"][0]["id"]
        return out

    return reply


def room_to_talk(client: TestClient, hours: int = 3):
    room, (a, b) = full_room(client)
    cid, engine = room["coalition_id"], engine_of(client)
    seats = ["p1", a["participant"], b["participant"]]
    briefs_open(engine, cid, seats)
    for who in (room["owner"], a, b):
        reply_brief(client, who["token"], {"q1": None, "q2": hours, "q3": None})
    people = {"p1": room["owner"], a["participant"]: a, b["participant"]: b}
    return cid, engine, people


def says(client: TestClient, cid: str) -> list[dict[str, Any]]:
    return events(client, cid, "say")


def test_agents_talk_then_one_revises_its_offer_and_the_plans_follow(tmp_path: Path) -> None:
    lines = {
        ("Member 1", 1): {"intent": "trade", "text": "I can take the venue if someone does costs."},
        ("Member 2", 1): {
            "intent": "agree",
            "text": "Fine, I will do the costs.",
            "re": 1,
            "to": "other",
            "revise": ["first"],
        },
    }
    model = RoomModel(needs=NEEDS, brief=BRIEF, talk=scripted(lines))
    with serve(tmp_path, model) as client:
        cid, engine, people = room_to_talk(client)
        until(lambda: engine.read(cid).get("talk_done") == "start", 40, "the talk to end")
        said = says(client, cid)
        assert [e["payload"]["intent"] for e in said] == ["trade", "agree"]
        assert said[1]["payload"]["re"] == said[0]["event_id"]
        assert said[1]["payload"]["to"] in people
        revised = engine.read(cid)["talk_revised"]
        assert len(revised) == 1 and revised[0]["seat"] == said[1]["on_behalf_of"]
        assert engine.read(cid)["talk"]["round"] == 2  # round one spoke, so a second was held
        view = view_of(engine, cid, "p1")
        assert [t["text"] for t in view["talk"]["thread"]] == [e["payload"]["text"] for e in said]
        assert view["talk"]["open"] is False and view["talk"]["thread"][0]["stage"] == "start"
        until(lambda: events(client, cid, "propose") or events(client, cid, "tension"), 40, "plans")
        last_say = max(e["seq"] for e in said)
        plans = events(client, cid, "propose") + events(client, cid, "tension")
        assert min(e["seq"] for e in plans) > last_say


def test_a_line_with_a_private_answer_is_held_as_a_stop(tmp_path: Path) -> None:
    lines = {("Member 1", 1): {"intent": "caveat", "text": "I only have 3 hours for all of it."}}
    model = RoomModel(needs=NEEDS, brief=BRIEF, talk=scripted(lines))
    with serve(tmp_path, model) as client:
        cid, engine, _ = room_to_talk(client)
        until(lambda: engine.read(cid).get("talk_done") == "start", 40, "the talk to end")
        assert says(client, cid) == []
        stops = engine.read(cid)["stops"]
        assert [s["policy"] for s in stops] == ["talk-private-value"]
        assert all("3 hours" not in json.dumps(e) for e in events(client, cid, "observe"))


def test_a_whisper_is_said_by_the_persons_own_agent(tmp_path: Path) -> None:
    model = RoomModel(needs=NEEDS, brief=BRIEF, offers_delay=4.0)
    with serve(tmp_path, model) as client:
        cid, engine, people = room_to_talk(client)
        until(lambda: engine.read(cid)["briefs_done"], 20, "the briefs")
        sent = client.post(
            "/v1/room/say",
            json={"text": "Tell them I can only do mornings"},
            headers=bearer(people["p1"]["token"]),
        )
        assert sent.status_code == 200 and sent.json()["route"] == "talk", sent.text
        assert view_of(engine, cid, "p1")["talk"]["mine"]["whisper"] == "I can only do mornings"
        assert view_of(engine, cid, list(people)[1])["talk"]["mine"]["whisper"] is None
        until(lambda: says(client, cid), 40, "the whisper to be said")
        line = says(client, cid)[0]
        assert line["on_behalf_of"] == "p1" and line["payload"]["text"] == "I can only do mornings"
        until(lambda: engine.read(cid).get("talk_done") == "start", 40, "the talk to end")
        assert view_of(engine, cid, "p1")["talk"]["mine"]["whisper"] is None


def test_no_talk_when_turned_off(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setenv("COALITIONKIT_ROOM_TALK_ROUNDS", "0")
    model = RoomModel(needs=NEEDS, brief=BRIEF, talk=scripted({}))
    with serve(tmp_path, model) as client:
        cid, engine, _ = room_to_talk(client)
        until(lambda: engine.may_plan(cid), 40, "the room to be ready for plans")
        assert engine.read(cid).get("talk") is None
        assert offers_by(client, cid, "p1")


def test_rules_check_a_line() -> None:
    thread = [{"id": "01M4XRC0Z8185GR38E1W8124GK"}]
    reply = TalkReply(speak=True, to="nobody", intent="ask", text=" Who  cooks? ", re=1, revise=[])
    line = checked(reply, {"p2"}, thread)
    assert line is not None and line.to == "room" and line.text == "Who cooks?"
    assert line.re == thread[0]["id"]
    assert checked(reply.model_copy(update={"speak": False}), {"p2"}, thread) is None
    assert checked(reply.model_copy(update={"re": 7, "to": "p2"}), {"p2"}, thread).re is None  # type: ignore[union-attr]


def test_rules_find_private_values_but_not_public_words() -> None:
    told = [
        {"kind": "amount", "answer": 3},
        {"kind": "choice", "answer": "The venue"},
        {"kind": "choice", "answer": "Yes"},
        {"kind": "text", "answer": "My knee is bad"},
        {"kind": "slots", "answer": ["Sat 10:00"]},
    ]
    values = private_values(told, "Find a venue. Plan a trip. Sat 10:00")
    assert values == ["3", "My knee is bad"]
    assert leaked("I have 3 hours", values) == "3"
    assert leaked("I have 30 minutes", values) is None
    assert leaked("my knee is bad, so no stairs", values) == "My knee is bad"
    assert leaked("my knee is bad", values, allowed="Say my knee is bad") is None
    assert whispered("tell them that I can only do mornings") == "I can only do mornings"


def test_the_agents_talk_again_after_a_change(tmp_path: Path) -> None:
    lines = {("Member 1", 1): {"intent": "caveat", "text": "Mind the budget for the venue."}}
    heard: list[Any] = []
    script = scripted(lines)

    def talk(user: str) -> dict[str, Any]:
        heard.append(json.loads(user)["what_changed"])
        return script(user)

    model = RoomModel(needs=NEEDS, brief=BRIEF, talk=talk)
    with serve(tmp_path, model) as client:
        cid, engine, people = room_to_talk(client)
        until(lambda: events(client, cid, "propose") or events(client, cid, "tension"), 40, "plans")
        assert len(says(client, cid)) == 1
        changed = client.post(
            "/v1/room/say",
            json={"text": "I can't find a venue after all"},
            headers=bearer(people["p1"]["token"]),
        )
        assert changed.status_code == 200 and changed.json()["route"] == "change", changed.text
        until(lambda: str(engine.read(cid).get("talk_done")).startswith("change:"), 40, "talk 2")
        thread = view_of(engine, cid, "p1")["talk"]["thread"]
        assert [t["stage"] for t in thread] == ["start", "change"]
        assert view_of(engine, cid, "p1")["talk"]["stage"] == "change"
        assert heard[0] is None  # the first talk follows no change
        after = [h for h in heard if h]
        assert after and after[0]["by"] in {"you", "Member 1"}
        assert after[0]["said"] == "I can't find a venue after all"
        assert after[0]["they_can_no_longer_do_them"] is True
