# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportMissingParameterType=false, reportPrivateUsage=false
"""Commitments, results, done and the end of the room, in a scripted room."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from room_flow import decide_plan, sign_kind
from room_rig import (
    BRIEF,
    NEEDS,
    RoomModel,
    bearer,
    engine_of,
    events,
    serve,
    server_of,
    until,
    view_of,
)
from test_room_choices import OFFERS, make_offers, silent_room

SHAPES: dict[str, dict[str, Any]] = {
    "place": {"options": [{"name": "Community hall", "why": "Fits the group"}]},
    "budget": {"suggested": [{"label": "Spare cushion", "amount": 20, "unit": "EUR"}]},
    "list": {"items": [{"label": "Name tags", "who": ""}]},
    "draft": {"subject": "Please join us", "body": "A short note for everyone."},
    "schedule": {"items": [{"title": "Meet"}]},
}


def made(user: str) -> dict[str, Any]:
    kind = json.loads(user)["kind"]
    tree = [
        {"id": "root", "component": "Column", "props": json.dumps({"children": ["h", "t"]})},
        {
            "id": "h",
            "component": "Heading",
            "props": json.dumps({"text": f"{kind}", "variant": "h3"}),
        },
        {
            "id": "t",
            "component": "Text",
            "props": json.dumps({"text": "Suggested, not settled.", "provenance": "estimate"}),
        },
    ]
    return {"title": f"The {kind}", "data": json.dumps(SHAPES[kind]), "components": tree}


def model() -> RoomModel:
    return RoomModel(needs=NEEDS, brief=BRIEF, made=made)


def to_decided(client: TestClient) -> tuple[str, Any, dict[str, Any]]:
    cid, engine, people = silent_room(client)
    make_offers(client, cid, dict(zip(OFFERS, people.values(), strict=True)))
    until(lambda: events(client, cid, "tension") or events(client, cid, "propose"), 40, "plans")
    until(lambda: events(client, cid, "tension"), 20, "the tension")
    decide_plan(client, cid, people)
    host = server_of(client).hosts[cid]
    until(
        lambda: {t["status"] for t in host.state.tasks.values()} <= {"decided", "committed"},
        40,
        "decided",
    )
    return cid, engine, people


def approve_commitments(client: TestClient, cid: str, people: dict[str, Any]) -> None:
    host = server_of(client).hosts[cid]
    for who, person in people.items():
        mine = [
            t
            for t in host.state.tasks.values()
            if t["assignee"] == who and t["status"] == "decided"
        ]
        if mine:
            until(
                lambda who=who: any(a["kind"] == "commitment" for a in host.open_consents(who)),
                20,
                f"{who} to be asked to commit",
            )
            sign_kind(client, cid, person["token"], who, "commitment")


def test_a_signed_plan_gives_results_of_three_kinds(tmp_path: Path) -> None:
    with serve(tmp_path, model()) as client:
        cid, engine, people = to_decided(client)
        host = server_of(client).hosts[cid]
        assert view_of(engine, cid, "p1")["phase"] == "commit"
        until(lambda: len(events(client, cid, "commit")) == 3, 20, "agents to ask for commitments")
        assert not [
            e
            for e in events(client, cid, "decide")
            if e["payload"]["subject"]["kind"] == "commitment"
        ]
        approve_commitments(client, cid, people)
        results = lambda: [  # noqa: E731
            e for e in events(client, cid, "observe") if '"result": 1' in e["payload"]["content"]
        ]
        until(lambda: len(results()) == 3, 40, "three results")
        content = {
            json.loads(e["payload"]["content"])["kind"]: json.loads(e["payload"]["content"])
            for e in results()
        }
        assert set(content) == {"place", "budget", "draft"}
        assert content["place"]["data"]["options"][0]["provenance"] == "estimate"
        assert content["place"]["data"]["chosen"] is None
        budget = content["budget"]["data"]
        assert budget["currency"] == "minutes" and budget["total"] == sum(
            r["amount"] for r in budget["rows"]
        )
        assert {r["provenance"] for r in budget["rows"]} == {"signed"}
        assert budget["suggested"] == [
            {"label": "Spare cushion", "amount": 20, "unit": "EUR", "provenance": "estimate"}
        ], "money is in the goal, so suggested cost lines sit apart from the signed total"
        assert budget["total"] == sum(r["amount"] for r in budget["rows"])
        cards = [n["title"] for n in content["budget"]["components"] if n["component"] == "Card"]
        assert cards == [
            "Time budget in minutes (from the offers)",
            "Suggested costs (estimates, not in the total)",
        ]
        assert set(content["draft"]["data"]) == {"subject", "body"}
        assert all(c["source"] == "model" and c["sources"] for c in content.values())
        events_ids = {e["event_id"] for e in server_of(client).store.read(cid)}
        for c in content.values():
            assert set(c["sources"]) <= events_ids
            assert c["components"][0]["id"] == "root"
        # The budget tree's numbers point at real offers.
        refs = [
            f["value"]["event_ref"]
            for node in content["budget"]["components"]
            for f in node.get("fields", [])
            if isinstance(f["value"], dict)
        ]
        assert refs and set(refs) <= events_ids
        view = view_of(engine, cid, "p1")
        assert len(view["results"]) == 3 and view["phase"] in {"make", "live"}
        for r in view["results"]:
            assert len(r["messages"]) == 3 and r["replaced_by"] is None and r["seqs"]
        assert {n["result"] for n in view["needs"]} == {r["id"] for r in view["results"]}
        until(lambda: view_of(engine, cid, "p1")["phase"] == "live", 20, "live")
        assert host.state.stage in {"Act", "Live"}


def test_done_is_the_persons_own_click_and_needs_a_result(tmp_path: Path) -> None:
    with serve(tmp_path, model()) as client:
        cid, engine, people = to_decided(client)
        host = server_of(client).hosts[cid]
        mine = next(t for t in host.state.tasks.items() if t[1]["assignee"] == "p1")[0]
        token = bearer(people["p1"]["token"])
        early = client.post("/v1/room/done", json={"task_id": mine}, headers=token)
        assert early.status_code == 409, "no approved commitment and no result yet"
        approve_commitments(client, cid, people)
        until(
            lambda: view_of(engine, cid, "p1")["mine"]["tasks"][0]["can_mark_done"], 40, "a result"
        )
        before = view_of(engine, cid, "p1")
        assert before["lights"] == "day", "a task they can mark done is their turn"
        assert not [e for e in events(client, cid, "done") if e["on_behalf_of"] == "p1"], (
            "never without a click"
        )
        other = client.post(
            "/v1/room/done", json={"task_id": mine}, headers=bearer(people["p2"]["token"])
        )
        assert other.status_code == 409, "not their task"
        ok = client.post("/v1/room/done", json={"task_id": mine}, headers=token)
        assert ok.status_code == 200 and ok.json()["seq"] > 0
        done = [e for e in events(client, cid, "done") if e["on_behalf_of"] == "p1"]
        assert len(done) == 1
        evidence = done[0]["payload"]["evidence"][0]
        assert evidence["kind"] == "result" and evidence["verified_by"] == "p1"
        assert any(e["event_id"] == evidence["ref"] for e in events(client, cid, "observe"))
        again = client.post("/v1/room/done", json={"task_id": mine}, headers=token)
        assert again.status_code == 409
        assert host.state.tasks[mine]["status"] == "done"


def test_a_bad_tree_is_asked_for_again_then_replaced_by_a_fixed_one(tmp_path: Path) -> None:
    def broken(user: str) -> dict[str, Any]:
        reply = made(user)
        reply["components"][2]["props"] = json.dumps(
            {"text": "Cost", "provenance": "estimate", "extra": 5}
        )
        return reply

    scripted = RoomModel(needs=NEEDS, brief=BRIEF, made=broken)
    with serve(tmp_path, scripted) as client:
        cid, _engine, people = to_decided(client)
        approve_commitments(client, cid, people)
        until(
            lambda: (
                len(
                    [
                        e
                        for e in events(client, cid, "observe")
                        if '"result": 1' in e["payload"]["content"]
                    ]
                )
                == 3
            ),
            40,
            "results",
        )
        calls = [c for c in scripted.calls if c[0] == "composer"]
        assert len(calls) == 6, "each result asked twice: once, then once with the errors"
        retried = [json.loads(str(c[1][-1]["content"]))["errors_to_fix"] for c in calls]
        assert sum(1 for e in retried if e) == 3 and all(
            "not allowed" in e[0] for e in retried if e
        )
        for e in events(client, cid, "observe"):
            if '"result": 1' in e["payload"]["content"]:
                content = json.loads(e["payload"]["content"])
                ids = [n["id"] for n in content["components"]]
                assert ids[0] == "root" and "h" in ids and content["source"] == "model"


def test_a_helper_signs_its_own_commitment_and_reports_done_itself(tmp_path: Path) -> None:
    from room_flow import briefs_open, decide_plan, reply_brief
    from room_rig import join, sign, start_room

    def offers(user: str) -> dict[str, Any]:
        ids = [n["id"] for n in json.loads(user)["needs"]]
        return {
            "offers": [{"need_id": i, "minutes": 40, "money": 0, "effort": "low"} for i in ids],
            "note": "Offered a little on each.",
        }

    scripted = RoomModel(needs=NEEDS, brief=BRIEF, offers=offers, made=made)
    with serve(tmp_path, scripted) as client:
        room = start_room(client, seats=3)
        cid, engine = room["coalition_id"], engine_of(client)
        member = join(client, room)
        sign(client, cid, room["owner"]["token"], "p1")
        sign(client, cid, member["token"], member["participant"])
        until(lambda: len(events(client, cid, "need")) >= 3, what="needs")
        client.post(
            "/v1/room/begin", json={"helpers": True}, headers=bearer(room["owner"]["token"])
        )
        sign(client, cid, member["token"], member["participant"])
        briefs_open(engine, cid, ["p1", member["participant"]])
        for token in (room["owner"]["token"], member["token"]):
            reply_brief(client, token, {"q1": None, "q2": 2, "q3": None})
        until(lambda: events(client, cid, "propose"), 60, "plans")
        people = {"p1": room["owner"], member["participant"]: member}
        until(lambda: server_of(client).hosts[cid].open_consents("p1"), 20, "an ask")
        decide_plan(client, cid, people)
        host = server_of(client).hosts[cid]
        until(
            lambda: {t["status"] for t in host.state.tasks.values()} <= {"decided", "committed"},
            20,
            "decided",
        )
        assert host.state.tasks, "tasks exist"
        helper_task = next(
            (k for k, t in host.state.tasks.items() if t["assignee"] == "helper-1"), None
        )
        assert helper_task, "the cheapest offer on one need is the helper's"
        approve_commitments(client, cid, people)
        until(lambda: host.state.tasks[helper_task]["status"] == "done", 40, "the helper to finish")
        commit = [e for e in events(client, cid, "commit") if e["on_behalf_of"] == "helper-1"]
        decided = [
            e
            for e in events(client, cid, "decide")
            if e["on_behalf_of"] == "helper-1" and e["payload"]["subject"]["kind"] == "commitment"
        ]
        assert len(commit) == 1 and len(decided) == 1 and decided[0]["payload"]["consent"] is True
        done = [e for e in events(client, cid, "done") if e["on_behalf_of"] == "helper-1"]
        assert len(done) == 1 and done[0]["payload"]["evidence"][0]["verified_by"] == "helper-1"
        until(
            lambda: any(t["status"] == "committed" for t in host.state.tasks.values()),
            40,
            "people's tasks",
        )
        time.sleep(2)
        assert not [e for e in events(client, cid, "done") if e["on_behalf_of"] != "helper-1"]


def test_a_place_with_nothing_to_suggest_says_so_and_a_time_budget_is_called_one(
    tmp_path: Path,
) -> None:
    quiet = {
        "needs": [
            {"title": "Find a place", "kind": "place", "detail": "Somewhere we can all reach."},
            {"title": "Settle the budget", "kind": "budget", "detail": "Who gives what time."},
            {"title": "Write the invitation", "kind": "draft", "detail": "A short note."},
        ],
        "slots": ["Saturday morning"],
    }

    def echoing(user: str) -> dict[str, Any]:
        reply = made(user)
        if json.loads(user)["kind"] == "place":
            reply["data"] = json.dumps({"options": [{"name": "Find a place", "why": "needed"}]})
        if json.loads(user)["kind"] == "budget":
            lines = [{"label": "Cushion", "amount": 5, "unit": "EUR"}]
            reply["data"] = json.dumps({"suggested": lines})
        return reply

    with serve(tmp_path, RoomModel(needs=quiet, brief=BRIEF, made=echoing)) as client:
        cid, _engine, people = to_decided(client)
        approve_commitments(client, cid, people)
        until(lambda: len(results_of_events(client, cid)) == 3, 40, "three results")
        found = {c["kind"]: c for c in results_of_events(client, cid)}
        place = found["place"]
        assert place["title"] == "No place has been named yet"
        assert place["data"] == {"options": [], "chosen": None}
        text = json.dumps(place["components"])
        assert "No place has been named yet" in text and "Say box" in text
        budget = found["budget"]
        assert budget["title"] == "Time budget" and budget["data"]["currency"] == "minutes"
        assert budget["data"]["suggested"] == [], "no money in the goal, so no cost lines"


def results_of_events(client: TestClient, cid: str) -> list[dict[str, Any]]:
    return [
        json.loads(e["payload"]["content"])
        for e in events(client, cid, "observe")
        if '"result": 1' in e["payload"]["content"]
    ]
