# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportMissingParameterType=false, reportPrivateUsage=false
"""The room engine: needs, seats, helpers and the brief in a real server with a scripted model."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from room_rig import (
    BRIEF,
    BRIEF_TEXT,
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

from coalitionkit_server.room import brief
from coalitionkit_server.room.needs import kind_of, rule_needs, rule_slots, split_goal
from coalitionkit_server.room.view import room_state


def test_split_goal_never_copies_the_sentence() -> None:
    goal = "We need to book the venue, send invitations and collect the costs"
    titles = split_goal(goal)
    assert titles == ["Book the venue", "Send invitations", "Collect the costs"]
    assert goal not in titles
    items = rule_needs("3 labs and a courier need a delivery by Friday", [])
    assert [i.title for i in items] == ["A delivery by Friday"]
    drafted = rule_needs("Whatever the goal says", ["a shared room", "the costs"])
    assert [(i.title, i.kind) for i in drafted] == [
        ("A shared room", "place"),
        ("The costs", "budget"),
    ]


def test_kinds_and_slots() -> None:
    assert kind_of("Who pays what") == "draft"
    assert kind_of("Split the budget") == "budget"
    assert kind_of("Pick a date") == "schedule"
    now = datetime(2030, 1, 7, 8, tzinfo=UTC)
    slots = rule_slots(datetime(2030, 1, 9, 12, tzinfo=UTC), now)
    assert 1 <= len(slots) <= 6 and all(s.endswith("UTC") for s in slots)
    assert rule_slots(datetime(2030, 1, 7, 8, 30, tzinfo=UTC), now) == []


def test_seed_waits_for_the_needs(tmp_path: Path) -> None:
    model = RoomModel(needs=NEEDS, gardener_delay=2.0)
    with serve(tmp_path, model) as client:
        room = start_room(client)
        cid = room["coalition_id"]
        sign(client, cid, room["owner"]["token"], "p1")
        until(lambda: model.calls, what="the gardener to be asked")
        assert not events(client, cid, "need"), "needs were seeded before the Gardener finished"
        until(lambda: len(events(client, cid, "need")) >= 3, what="needs")
        found = events(client, cid, "need")
        titles = {e["payload"]["description"] for e in found}
        assert titles == {n["title"] for n in NEEDS["needs"]}
        doc = engine_of(client).read(cid)
        assert doc["needs_source"] == "model"
        by_id = {n["id"]: n for n in doc["needs"]}
        for event in found:
            need = by_id[event["payload"]["need_id"]]
            assert need["title"] == event["payload"]["description"]
            assert need["kind"] in {"place", "budget", "draft"} and need["detail"]
        assert [s["id"] for s in doc["slots"]] == ["s1", "s2", "s3"]


def test_rules_split_the_goal_without_a_model(tmp_path: Path) -> None:
    with serve(tmp_path, RoomModel()) as client:
        room = start_room(
            client, goal="We need to book the venue, send invitations and collect the costs"
        )
        cid = room["coalition_id"]
        sign(client, cid, room["owner"]["token"], "p1")
        found = until(lambda: len(events(client, cid, "need")) >= 3, what="needs")
        assert found
        titles = [e["payload"]["description"] for e in events(client, cid, "need")]
        assert titles == ["Book the venue", "Send invitations", "Collect the costs"]
        assert engine_of(client).read(cid)["needs_source"] == "rules"


def seated_room(tmp_path: Path, client, seats: int = 3, signed: int = 2):  # type: ignore[no-untyped-def]
    room = start_room(client, seats=seats)
    cid = room["coalition_id"]
    sign(client, cid, room["owner"]["token"], "p1")
    members = [join(client, room) for _ in range(signed - 1)]
    for member in members:
        sign(client, cid, member["token"], member["participant"])
    until(lambda: len(events(client, cid, "need")) >= 3, what="needs")
    return room, members


def test_begin_without_helpers(tmp_path: Path) -> None:
    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF)) as client:
        room, (member,) = seated_room(tmp_path, client)
        cid, owner = room["coalition_id"], room["owner"]
        engine = engine_of(client)
        mine = view_of(engine, cid, "p1")
        assert mine is not None and mine["begin"] == {"can": True, "open_seats": 1}
        theirs = view_of(engine, cid, member["participant"])
        assert theirs is not None and theirs["begin"] is None
        kinds = [(s["kind"], s["signed"]) for s in mine["seats"]]
        assert kinds == [("person", True), ("person", True), ("open", False)]
        denied = client.post(
            "/v1/room/begin", json={"helpers": False}, headers=bearer(member["token"])
        )
        assert denied.status_code == 403
        done = client.post(
            "/v1/room/begin", json={"helpers": False}, headers=bearer(owner["token"])
        )
        assert done.status_code == 200 and done.json()["phase"] in {"brief", "work"}
        charters = events(client, cid, "charter")
        assert [c["payload"]["revision"] for c in charters] == [1, 2]
        assert charters[-1]["payload"]["deciders"] == ["p1", member["participant"]]
        host = server_of(client).hosts[cid]
        state = host.state
        assert state.accepted_charter("p1"), "the owner's click counts as accepting"
        assert not state.accepted_charter(member["participant"])
        assert [a["kind"] for a in host.open_consents(member["participant"])] == ["charter"]
        door = client.get("/v1/coalition/door", headers=bearer(owner["token"])).json()
        assert door["stopped"] is True
        assert not state.members.keys() - {"p1", member["participant"]}
        again = client.post(
            "/v1/room/begin", json={"helpers": False}, headers=bearer(owner["token"])
        )
        assert again.status_code == 200 and len(events(client, cid, "charter")) == 2
        seats = view_of(engine, cid, "p1")["seats"]
        assert [s["kind"] for s in seats] == ["person", "person"]


def test_begin_with_helpers(tmp_path: Path) -> None:
    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF)) as client:
        room, _members = seated_room(tmp_path, client)
        cid = room["coalition_id"]
        done = client.post(
            "/v1/room/begin", json={"helpers": True}, headers=bearer(room["owner"]["token"])
        )
        assert done.status_code == 200, done.text
        server = server_of(client)
        state = server.hosts[cid].state
        helpers = [p for p in state.members if p.startswith("helper-")]
        assert helpers == ["helper-1"]
        assert "helper-1" not in state.charter["deciders"]
        assert state.accepted_charter("helper-1"), "the helper signs with its own key"
        assert state.members["helper-1"]["surfaces"] == []
        card = client.get(f"/cards/{cid}/helper-1")
        assert card.status_code == 200 and card.json()["name"] == "Budget helper (agent)"
        assert "not a person" in card.json()["description"]
        engine = server.room
        assert engine is not None
        view = view_of(engine, cid, "p1")
        assert view is not None
        helper_seats = [s for s in view["seats"] if s["kind"] == "helper"]
        assert len(helper_seats) == 1 and "agent" in helper_seats[0]["label"].lower()
        assert helper_seats[0]["signed"] is True
        # The helper is never asked to brief, and never a decider of a plan.
        until(lambda: engine.read(cid)["briefs"].get("p1"), what="the brief")
        assert "helper-1" not in engine.read(cid)["briefs"]


def test_charter_revision_resets_acceptance(tmp_path: Path) -> None:
    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF)) as client:
        room, (member,) = seated_room(tmp_path, client)
        cid = room["coalition_id"]
        client.post(
            "/v1/room/begin", json={"helpers": False}, headers=bearer(room["owner"]["token"])
        )
        host = server_of(client).hosts[cid]
        assert host.state.charter["revision"] == 2
        assert not host.state.accepted_charter(member["participant"])
        assert sign(client, cid, member["token"], member["participant"]) == 1
        assert host.state.accepted_charter(member["participant"])
        assert all(host.state.accepted_charter(d) for d in host.state.charter["deciders"])


def test_everyone_signed_begins_by_itself(tmp_path: Path) -> None:
    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF)) as client:
        room, _ = seated_room(tmp_path, client, seats=2, signed=2)
        cid = room["coalition_id"]
        engine = engine_of(client)
        until(lambda: engine.read(cid)["begun"], what="begin")
        assert len(events(client, cid, "charter")) == 1, "no revision when no seat is open"
        until(lambda: engine.read(cid)["briefs"].get("p1"), what="the brief")


def open_brief(client, room, member):  # type: ignore[no-untyped-def]
    cid = room["coalition_id"]
    engine = engine_of(client)
    client.post("/v1/room/begin", json={"helpers": False}, headers=bearer(room["owner"]["token"]))
    sign(client, cid, member["token"], member["participant"])
    for who in ("p1", member["participant"]):
        until(lambda who=who: engine.read(cid)["briefs"].get(who), what="briefs")
    return cid, engine


SECRET = "private-sentinel-answer"


def test_brief_is_private_and_checked(tmp_path: Path) -> None:
    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF_TEXT)) as client:
        room, (member,) = seated_room(tmp_path, client)
        cid, engine = open_brief(client, room, member)
        who = member["participant"]
        mine = view_of(engine, cid, who)["mine"]
        assert [q["component"] for q in mine["brief"]] == ["ChoicePicker", "Slider", "TextArea"]
        first = mine["brief"][0]
        assert [
            m.get("createSurface", m.get("updateComponents", m.get("updateDataModel"))) is not None
            for m in first["messages"]
        ] == [True] * 3
        ids = [c["id"] for c in first["messages"][1]["updateComponents"]["components"]]
        assert ids == ["root", "ask", "why", "input", "go"]
        token = member["token"]
        post = lambda body: client.post("/v1/room/brief", json=body, headers=bearer(token))  # noqa: E731
        assert post({"question_id": "q1", "value": "not-an-option"}).status_code == 422
        assert post({"question_id": "q2", "value": 99}).status_code == 422
        assert post({"question_id": "q2", "value": "ten"}).status_code == 422
        assert post({"question_id": "q3", "value": ""}).status_code == 422
        assert post({"question_id": "q9", "value": 1}).status_code == 404
        assert post({"question_id": "q1"}).status_code == 422
        assert post({"question_id": "q1", "value": "o2", "skip": True}).status_code == 422
        assert post({"question_id": "q1", "value": "o2"}).json() == {"status": "answered"}
        assert post({"question_id": "q1", "value": "o1"}).status_code == 409
        assert post({"question_id": "q2", "value": 4}).json() == {"status": "answered"}
        # Another seat never sees these questions or answers, nor does the log.
        other = json.dumps(view_of(engine, cid, "p1"))
        assert "How many hours" in other  # their own brief is their own
        theirs = view_of(engine, cid, "p1")["mine"]["brief"]
        assert all(q["status"] == "open" for q in theirs)
        assert post({"question_id": "q3", "value": SECRET}).json() == {"status": "answered"}
        until(lambda: engine.read(cid)["briefs"][who]["closed"], what="the brief to close")
        vault = engine.vault(cid, who)["_room_brief"]
        assert vault["questions"][0]["answer"] == "o2" and vault["questions"][1]["answer"] == 4
        log = json.dumps(server_of(client).store.read(cid))
        assert (
            "_room_brief" not in log
            and "How many hours" not in log
            and SECRET not in log
            and SECRET not in log
        )
        keys = client.get("/v1/agent/vault", headers=bearer(token)).json()["keys"]
        assert not [k for k in keys if k.startswith("_room")]
        refused = client.post(
            "/v1/agent/vault", json={"values": {"_room_brief": {}}}, headers=bearer(token)
        )
        assert refused.status_code == 422
        # p1's room state never holds the member's answers.
        assert SECRET not in json.dumps(view_of(engine, cid, "p1"))
        assert SECRET not in json.dumps(server_of(client).store.read(cid))


def test_slots_and_text_shapes() -> None:
    q = {"kind": "slots", "options": [{"id": "s1"}, {"id": "s2"}], "low": 0, "high": 0}
    assert brief.check_answer(q, ["s2", "s1"]) == ["s1", "s2"]
    for bad in ([], ["s1", "s1"], ["s9"], "s1", [1]):
        with pytest.raises(ValueError):
            brief.check_answer(q, bad)
    text = {"kind": "text", "options": [], "low": 0, "high": 0}
    assert brief.check_answer(text, "  fine   words ") == "fine words"
    for bad in ("", "x" * 301, 4, "bad\x01"):
        with pytest.raises(ValueError):
            brief.check_answer(text, bad)
    amount = {"kind": "amount", "options": [], "low": 2, "high": 8}
    assert brief.check_answer(amount, 2) == 2
    # Send without moving the slider posts the data model's wrapped default.
    assert brief.check_answer(amount, {"value": 5, "event_ref": "e1"}) == 5
    for bad in ({"value": 9, "event_ref": "e1"}, {"value": 5}, {"value": "5", "event_ref": "e1"}):
        with pytest.raises(ValueError):
            brief.check_answer(amount, bad)
    for bad in (1, 9, True, "3"):
        with pytest.raises(ValueError):
            brief.check_answer(amount, bad)


def test_brief_closes_after_its_time(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(brief, "BRIEF_SECONDS", 1)
    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF)) as client:
        room, (member,) = seated_room(tmp_path, client)
        cid, engine = open_brief(client, room, member)
        until(lambda: engine.read(cid)["briefs_done"], what="the briefs to time out")
        until(lambda: engine.may_plan(cid), 40, "offers and the comparison")
        mine = view_of(engine, cid, member["participant"])["mine"]
        assert {q["status"] for q in mine["brief"]} == {"skipped"}


def test_rule_questions_without_a_model(tmp_path: Path) -> None:
    with serve(tmp_path, RoomModel()) as client:
        room, (member,) = seated_room(tmp_path, client)
        cid, engine = open_brief(client, room, member)
        mine = view_of(engine, cid, member["participant"])["mine"]
        kinds = [q["component"] for q in mine["brief"]]
        assert 1 <= len(kinds) <= 3 and "Slider" in kinds
        assert engine.read(cid)["briefs"][member["participant"]]["source"] == "rules"


def test_room_state_for_each_viewer_and_cost(tmp_path: Path) -> None:
    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF)) as client:
        room, (member,) = seated_room(tmp_path, client)
        cid, engine = open_brief(client, room, member)
        one = view_of(engine, cid, "p1")
        two = view_of(engine, cid, member["participant"])
        assert one is not None and two is not None
        assert one["phase"] == "brief" and one["goal"].startswith("Three members")
        assert [s["you"] for s in one["seats"]] == [True, False]
        assert [s["you"] for s in two["seats"]] == [False, True]
        assert one["lights"] == "day", "an open question is this viewer's turn"
        assert [n["source"] for n in one["needs"]] == ["model"] * 3
        assert room_state(engine, cid, "nobody") is None
        # The cache holds until the room moves.
        assert view_of(engine, cid, "p1") is one
        engine.note(cid, "reading", "A note")
        assert view_of(engine, cid, "p1") is not one
        labels = [a["label"] for a in one["activity"]]
        assert "Reading the goal into needs" in labels
        asked = [a["seat"] for a in one["activity"] if a["label"].startswith("Your agent is")]
        assert asked == ["p1"], "another seat's question activity must not reach p1"
        done = next(a for a in one["activity"] if a["verb"] == "reading")
        assert done["source"] == "model" and done["state"] == "done" and done["ms"] is not None
        spent = server_of(client).cost_meter(cid)
        assert spent is not None and spent["currency"] == "USD" and spent["spent"] > 0


def test_restart_resumes_the_room(tmp_path: Path) -> None:
    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF)) as client:
        room, _members = seated_room(tmp_path, client)
        cid = room["coalition_id"]
        client.post(
            "/v1/room/begin", json={"helpers": False}, headers=bearer(room["owner"]["token"])
        )
        engine = engine_of(client)
        until(lambda: engine.read(cid)["begun"], what="begin")
    model = RoomModel(needs=NEEDS, brief=BRIEF)
    with serve(tmp_path, model) as client:
        engine = engine_of(client)
        until(lambda: engine.read(cid)["briefs"].get("p1"), what="the brief after restart")
        doc = engine.read(cid)
        assert doc["begun"] and doc["needs_state"] == "ready"
        assert [n["title"] for n in doc["needs"]] == [n["title"] for n in NEEDS["needs"]]
        assert not [c for c in model.calls if c[0] == "gardener"], "needs are not made twice"
        assert len(events(client, cid, "need")) == 3


def test_a_plan_waits_for_the_brief(tmp_path: Path) -> None:
    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF)) as client:
        room, (member,) = seated_room(tmp_path, client)
        cid, _engine = open_brief(client, room, member)
        needs = events(client, cid, "need")
        for who in (room["owner"], member):
            for need in needs:
                response = client.post(
                    "/v1/agent/offer",
                    json={
                        "need_id": need["payload"]["need_id"],
                        "cost": {"minutes": 5, "money": 0, "effort": "low"},
                    },
                    headers=bearer(who["token"]),
                )
                assert response.status_code == 200, response.text
        import time

        time.sleep(2.5)
        assert not events(client, cid, "propose"), "a plan appeared while the brief was open"
        for who in (room["owner"], member):
            for q in ("q1", "q2", "q3"):
                client.post(
                    "/v1/room/brief",
                    json={"question_id": q, "skip": True},
                    headers=bearer(who["token"]),
                )
        until(lambda: events(client, cid, "propose"), what="a plan after the brief")


def test_the_hub_sends_a_delta_when_the_room_version_moves(tmp_path: Path) -> None:
    from ag_ui.core import StateDeltaEvent

    from coalitionkit_runtime import Subscription

    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF)) as client:
        room, (member,) = seated_room(tmp_path, client)
        cid, engine = open_brief(client, room, member)
        hub = server_of(client).surfaces[cid].state.hub
        session = hub.feed_session("p1")
        start = session.start()
        snapshot = start[1].snapshot  # type: ignore[union-attr]
        assert snapshot["room"]["phase"] == "brief" and snapshot["stage"]
        assert snapshot["cost_meter"]["currency"] == "USD"
        sub = Subscription(cid, 0)
        assert not [f for f in hub._poll(session, sub) if isinstance(f, StateDeltaEvent)]
        engine.note(cid, "reading", "Something moved")  # no log event, only a version bump
        frames = hub._poll(session, sub)
        deltas = [f for f in frames if isinstance(f, StateDeltaEvent)]
        assert deltas and any(op.path.startswith("/room/activity") for op in deltas[0].delta)
        assert not [f for f in hub._poll(session, sub) if isinstance(f, StateDeltaEvent)]
