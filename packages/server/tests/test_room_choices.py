# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportMissingParameterType=false, reportPrivateUsage=false
"""Real choices: differing offers give more than one plan, a tension, and a vote that decides."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from room_flow import briefs_open, full_room, reply_brief
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

#: (minutes, effort) each person would take for each of the three needs.
OFFERS = {
    "p1": [(20, "high"), (100, "low"), (60, "high")],
    "p2": [(100, "low"), (20, "high"), (60, "high")],
    "p3": [(60, "high"), (60, "high"), (30, "medium")],
}


def make_offers(client: TestClient, cid: str, people: dict[str, dict[str, Any]]) -> None:
    needs = [e["payload"]["need_id"] for e in events(client, cid, "need")]
    engine = engine_of(client)
    # Hold planning while the offers go in, or a slow machine lets a plan start half-way.
    engine.update(cid, lambda d: d.__setitem__("change_pending", True))
    for who, rows in OFFERS.items():
        for need, (minutes, effort) in zip(needs, rows, strict=True):
            cost = {"minutes": minutes, "money": 0, "effort": effort}
            reply = client.post(
                "/v1/agent/offer",
                json={"need_id": need, "cost": cost},
                headers=bearer(people[who]["token"]),
            )
            assert reply.status_code == 200, reply.text
    engine.update(cid, lambda d: d.__setitem__("change_pending", False))
    engine.wake_gardener(cid)


def silent_room(client: TestClient):
    room, (a, b) = full_room(client)
    cid, engine = room["coalition_id"], engine_of(client)
    briefs_open(engine, cid, ["p1", a["participant"], b["participant"]])
    for who in (room["owner"], a, b):
        reply_brief(client, who["token"], {"q1": None, "q2": 0, "q3": None})
    until(lambda: engine.may_plan(cid), 40, "the room to be ready for plans")
    people = {"p1": room["owner"], a["participant"]: a, b["participant"]: b}
    return cid, engine, people


def test_differing_offers_give_a_real_choice_and_a_tension(tmp_path: Path) -> None:
    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF)) as client:
        cid, engine, people = silent_room(client)
        ids = list(people)
        make_offers(client, cid, dict(zip(OFFERS, people.values(), strict=True)))
        until(lambda: events(client, cid, "propose"), 30, "plans")
        plans = events(client, cid, "propose")[0]["payload"]["plans"]
        assert len(plans) >= 2, "differing offers must give a choice"
        scores = [p["objective_scores"] for p in plans]
        assert {"total_cost", "max_share_ratio", "third"} <= set(scores[0])
        assert len({s["third"] for s in scores}) > 1, "the effort objective tells plans apart"
        assert len(
            {tuple(sorted((a["task_id"], a["assignee"]) for a in p["assignments"])) for p in plans}
        ) == len(plans)
        until(lambda: events(client, cid, "tension"), 30, "a tension")
        tension = events(client, cid, "tension")[0]["payload"]
        assert {o["option_id"] for o in tension["options"]} == {p["plan_id"] for p in plans}
        assert set(tension["deciders"]) == set(ids)
        for who in ids:
            host_asks = server_of(client).hosts[cid].open_consents(who)
            assert any(a["kind"] == "tension_option" for a in host_asks), "the decider is asked"
        notes = view_of(engine, cid, "p1")["plan_notes"]
        until(lambda: len(view_of(engine, cid, "p1")["plan_notes"]) == len(plans), 30, "plan words")
        notes = view_of(engine, cid, "p1")["plan_notes"]
        names = [n["name"] for n in notes.values()]
        assert len(set(names)) == len(names), names
        assert any(w in " ".join(names) for w in ("Quickest", "Shared evenly", "Suits people best"))
        assert all(" takes " in n["line"] for n in notes.values())
        for n in notes.values():
            assert not re.search(r"effort|points|best at", n["name"] + n["line"], re.I)


def test_voting_a_tension_through_decides_the_plan(tmp_path: Path) -> None:
    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF)) as client:
        cid, _engine, people = silent_room(client)
        make_offers(client, cid, dict(zip(OFFERS, people.values(), strict=True)))
        until(lambda: events(client, cid, "tension"), 40, "a tension")
        tension = events(client, cid, "tension")[0]["payload"]
        chosen = tension["options"][0]["option_id"]
        host = server_of(client).hosts[cid]
        for who, person in people.items():
            ask = next(a for a in host.open_consents(who) if a["kind"] == "tension_option")
            reply = client.post(
                "/v1/agent/answers",
                json={
                    "interrupt_id": f"tension_option:{ask['id']}:{ask['revision']}:{who}",
                    "consent": True,
                    "choice": chosen,
                },
                headers=bearer(person["token"]),
            )
            assert reply.status_code == 200, reply.text
        state = host.state
        plan = next(
            p
            for p in events(client, cid, "propose")[0]["payload"]["plans"]
            if p["plan_id"] == chosen
        )
        wanted = {a["task_id"]: a["assignee"] for a in plan["assignments"]}
        assert {t: v["assignee"] for t, v in state.tasks.items()} == wanted
        assert {v["status"] for v in state.tasks.values()} == {"decided"}
        assert state.stage == "Act"


def test_two_plans_never_share_a_name(tmp_path: Path) -> None:
    def same(user: str) -> dict[str, Any]:
        plans = json.loads(user)["plans"]
        return {"plans": [{"plan_id": p["plan_id"], "name": "A plan", "line": "x"} for p in plans]}

    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF, names=same)) as client:
        cid, engine, people = silent_room(client)
        make_offers(client, cid, dict(zip(OFFERS, people.values(), strict=True)))
        until(lambda: len(view_of(engine, cid, "p1")["plan_notes"]) >= 2, 40, "plan words")
        notes = list(view_of(engine, cid, "p1")["plan_notes"].values())
        assert len({n["name"] for n in notes}) == len(notes) >= 2
        assert all(" takes " in n["line"] and n["source"] == "rules" for n in notes)


def test_the_front_is_computed_only_among_plans_inside_the_share_cap() -> None:
    """The offers of a live run: the front used to hold an unfair plan that dominated the fair
    ones, and removing it afterwards left one plan or none. Now unfair plans never enter."""
    from fractions import Fraction

    from coalitionkit_contracts.payloads import Cost, Window
    from coalitionkit_gardener import Offer, PlanConfig, Problem, Task, generate_plans

    window = Window(start="2026-11-03T00:00:00Z", end="2026-11-10T00:00:00Z")
    tasks = tuple(Task(t, (), window) for t in ("plan", "budget", "review"))
    rows = {
        ("helper", "budget"): (15, "low"),
        ("p2", "plan"): (85, "low"),
        ("p2", "budget"): (100, "medium"),
        ("p2", "review"): (70, "medium"),
        ("p1", "plan"): (90, "low"),
        ("p1", "budget"): (60, "medium"),
        ("p1", "review"): (75, "medium"),
    }
    offers = tuple(
        Offer(who, task, Cost(minutes=m, money=0, effort=e))  # pyright: ignore[reportArgumentType]
        for (who, task), (m, e) in rows.items()
    )
    level = {"low": 1, "medium": 2, "high": 3}

    def effort(assign: Any) -> float:
        return float(sum(level[rows[(who, task)][1]] for task, who in assign.items()))

    problem = Problem(tasks, offers, {"p1": 1, "p2": 1, "helper": 1})
    loose = generate_plans(problem, effort, config=PlanConfig())
    tight = generate_plans(problem, effort, config=PlanConfig(max_task_share=Fraction(3, 5)))
    assert any(len(set(p.assignments.values())) < 3 for p in loose.plans), "the old front"
    assert [dict(p.assignments) for p in tight.plans] == [
        {"budget": "helper", "plan": "p2", "review": "p1"}
    ], "the only other fair permutation is dominated, and a dominated plan is never added"


def test_two_people_who_want_the_same_job_with_crossing_estimates_meet_a_tension(
    tmp_path: Path,
) -> None:
    """Both pick the venue as the job they want; each is quicker at a different job."""
    minutes: dict[str, list[int]] = {}

    def crossing(user: str) -> dict[str, Any]:
        asked = json.loads(user)
        mine = minutes[asked["person"]]
        ids = [n["id"] for n in asked["needs"]]
        offers = [
            {"need_id": i, "minutes": m, "money": 0, "effort": "low" if k == 0 else "high"}
            for k, (i, m) in enumerate(zip(ids, mine, strict=True))
        ]
        return {"offers": offers, "note": "Offered on each."}

    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF, offers=crossing)) as client:
        room, (a, b) = full_room(client)
        cid, engine = room["coalition_id"], engine_of(client)
        who = [room["owner"], a, b]
        ids = ["p1", a["participant"], b["participant"]]
        names = [engine.name_of(cid, i) for i in ids]
        # p1 and p2 both want the venue (first need) and both are quick at a different job.
        minutes[names[0]] = [90, 20, 60]
        minutes[names[1]] = [90, 60, 20]
        minutes[names[2]] = [60, 60, 30]
        briefs_open(engine, cid, ids)
        for person, pick in zip(who, ("o1", "o1", "o2"), strict=True):
            reply_brief(client, person["token"], {"q1": pick, "q2": 2, "q3": None})
        until(lambda: events(client, cid, "propose"), 60, "plans")
        plans = events(client, cid, "propose")[0]["payload"]["plans"]
        venue = events(client, cid, "need")[0]["payload"]["need_id"]
        takers = {
            next(a["assignee"] for a in p["assignments"] if a["task_id"] == venue) for p in plans
        }
        assert len(plans) >= 2 and len(takers) == 2, "the same job is taken by each in turn"
        # A tension is raised only when plans differ by at least half on some objective (the
        # gardener's TradeoffPolicy); plans that merely swap who does what are a plain choice.
        scores = [p["objective_scores"] for p in plans]
        wide = any(
            max(float(x[k]) for x in scores) > 0
            and (max(float(x[k]) for x in scores) - min(float(x[k]) for x in scores))
            / max(float(x[k]) for x in scores)
            >= 0.5
            for k in ("total_cost", "max_share_ratio", "third")
        )
        time.sleep(8)
        assert bool(events(client, cid, "tension")) == wide
        asks = server_of(client).hosts[cid].open_consents("p1")
        assert any(a["kind"] == "plan" for a in asks) or wide, "the plans are put to the group"
