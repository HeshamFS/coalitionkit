# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
"""Gates 1 and 2: a real room with the live model and, when its key is present, the real Steward.

Everything goes through the web routes: sign, begin, brief, offer, compare, plans, decisions,
commitments, results, done, Say, change, end. Nothing is scripted but the answers a person would
type. Reads COALITIONKIT_META_API_KEY (and COALITIONKIT_BASETEN_API_KEY for the Steward) from the
environment only. ``ROOM_LIVE_GOAL`` picks the goal (0 or 1). Run with ``-s``: each test prints one
``OUTCOME`` line and the model's own words.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from room_flow import briefs_open, decide_plan, sign_kind
from room_rig import bearer, engine_of, events, join, server_of, sign, start_room, until, view_of

from coalitionkit_server import Settings, create_server
from coalitionkit_server.adapter import Document

GOALS = [
    "Two of us need to prepare a short shared report: a plan, a budget and a review",
    "Two of us need to organise a small get-together: find a place, share the costs, and "
    "write a short invitation to send out",
]
KEY = bool(os.environ.get("COALITIONKIT_META_API_KEY"))
REAL_STEWARD = bool(os.environ.get("COALITIONKIT_BASETEN_API_KEY"))
STEWARD_MODEL = "meta-models/muse-spark-open"


def answers_for(questions: list[Document], slots: list[str], shift: int) -> dict[str, Any]:
    """What a plain person would tell their agent: first option, a few hours, some times."""
    said: dict[str, Any] = {}
    for q in questions:
        first = next(m for m in q["messages"] if "updateComponents" in m)
        field = next(c for c in first["updateComponents"]["components"] if c["id"] == "input")
        if q["component"] == "Slider":
            said[q["id"]] = (field["min"]["value"] + field["max"]["value"]) // 4 or 1
        elif q["component"] == "TextArea":
            said[q["id"]] = "Afternoons suit me better than mornings."
        elif field.get("multiple"):
            said[q["id"]] = slots[shift : shift + 3]
        else:
            said[q["id"]] = field["options"][0]["id"]
    return said


def live_client(tmp_path: Path) -> TestClient:
    settings = Settings(
        store=SecretStr("sqlite:///" + str(tmp_path / "live.db")),
        host_key_file=tmp_path / "host.key",
        genesis="local",
        public_base_url="http://127.0.0.1:8000",
        room_engine="on",
    )
    return TestClient(
        create_server(settings),
        client=("127.0.0.1", 12345),
        headers={"Origin": settings.public_base_url},
    )


def results_of(client: TestClient, cid: str) -> list[Document]:
    return [e for e in events(client, cid, "observe") if '"result": 1' in e["payload"]["content"]]


class Run:
    """One live room, driven only through the routes."""

    def __init__(self, client: TestClient, goal: str) -> None:
        self.client, self.goal = client, goal
        self.server, self.engine = server_of(client), engine_of(client)
        self.room = start_room(
            client, seats=3, goal=goal, owner_name="Mira", real_steward=REAL_STEWARD
        )
        self.cid = self.room["coalition_id"]
        self.member = join(client, self.room, "Jonas")
        self.people = {"p1": self.room["owner"], self.member["participant"]: self.member}
        self.marks: dict[str, float] = {}
        self.started = time.monotonic()

    def mark(self, name: str) -> None:
        self.marks[name] = round(time.monotonic() - self.started, 1)

    def to_plans(self) -> None:
        c, cid = self.client, self.cid
        if REAL_STEWARD:
            ready = self.server.steward._ready  # pyright: ignore[reportPrivateUsage]
            until(lambda: ready is not None and ready.done(), 60, "the Steward")
        sign(c, cid, self.room["owner"]["token"], "p1")
        sign(c, cid, self.member["token"], self.member["participant"])
        until(lambda: len(events(c, cid, "need")) >= 2, 90, "needs seeded")
        self.mark("needs_seeded")
        begun = c.post(
            "/v1/room/begin", json={"helpers": True}, headers=bearer(self.room["owner"]["token"])
        )
        assert begun.status_code == 200, begun.text
        sign(c, cid, self.member["token"], self.member["participant"])
        briefs_open(self.engine, cid, list(self.people), 120)
        self.mark("briefs_open")
        slots = [s["id"] for s in self.engine.read(cid)["slots"]]
        for shift, (who, person) in enumerate(self.people.items()):
            questions = view_of(self.engine, cid, who)["mine"]["brief"]
            for question, value in answers_for(questions, slots, shift).items():
                reply = c.post(
                    "/v1/room/brief",
                    json={"question_id": question, "value": value},
                    headers=bearer(person["token"]),
                )
                assert reply.status_code == 200, (question, value, reply.text)
        until(lambda: events(c, cid, "propose"), 240, "plans")
        self.mark("plans")

    def decide_and_commit(self) -> None:
        c, cid = self.client, self.cid
        until(
            lambda: any(self.server.hosts[cid].open_consents(w) for w in self.people),
            120,
            "plan asks",
        )
        decide_plan(c, cid, self.people)
        host = self.server.hosts[cid]
        until(
            lambda: any(t["status"] == "decided" for t in host.state.tasks.values()), 90, "decided"
        )
        for who, person in self.people.items():
            mine = [t for t in host.state.tasks.values() if t["assignee"] == who]
            if any(t["status"] == "decided" for t in mine):
                until(
                    lambda who=who: any(a["kind"] == "commitment" for a in host.open_consents(who)),
                    90,
                    f"{who} to be asked to commit",
                )
                sign_kind(c, cid, person["token"], who, "commitment")

    def report(self, outcome: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        meter = self.server.gateway.meter
        records = [r for r in (meter.records if meter else []) if r.coalition_id == self.cid]
        steward = [r for r in records if r.model == STEWARD_MODEL]
        timings = [t for t in self.server.steward.timings]
        ms = sorted(round(t[1] * 1000) for t in timings)
        doc = self.engine.read(self.cid)
        proposals = events(self.client, self.cid, "propose")
        summary = {
            "outcome": outcome,
            "goal": self.goal,
            "real_steward": REAL_STEWARD,
            "seconds": self.marks,
            "plans": [len(p["payload"]["plans"]) for p in proposals],
            "tensions": len(events(self.client, self.cid, "tension")),
            "model_calls": len(records),
            "tokens": [
                sum(r.prompt_tokens for r in records),
                sum(r.completion_tokens for r in records),
            ],
            "cost_usd": round(sum(r.cost_micro_usd for r in records) / 1e6, 4),
            "steward": {
                "reviews": len(ms),
                "ms_median": ms[len(ms) // 2] if ms else None,
                "ms_p95": ms[int(len(ms) * 0.95) - 1] if ms else None,
                "ms_max": ms[-1] if ms else None,
                "actions": {
                    a: sum(1 for t in timings if t[2] == a) for a in {t[2] for t in timings}
                },
                "model_calls": len(steward),
                "cost_usd": round(sum(r.cost_micro_usd for r in steward) / 1e6, 4),
                "slow": [(t[0], round(t[1], 1)) for t in timings if t[1] > 3],
            },
            "stops": [(s["policy"], s["seat"], s["explain"]) for s in doc["stops"]],
            "gaps": doc["gaps_noted"],
            "failed": [
                {"label": a["label"], "error": a.get("error")}
                for a in doc["activity"]
                if a["state"] == "failed"
            ],
            **(extra or {}),
        }
        print("OUTCOME " + json.dumps(summary))
        return summary


@pytest.mark.live
@pytest.mark.skipif(not KEY, reason="no key")
def test_gate_one_a_real_room_reaches_plans(tmp_path: Path) -> None:
    goal = GOALS[int(os.environ.get("ROOM_LIVE_GOAL", "0"))]
    with live_client(tmp_path) as client:
        run = Run(client, goal)
        outcome = "plans"
        try:
            run.to_plans()
        except AssertionError as exc:
            outcome = f"stalled: {exc}"
        extra: dict[str, Any] = {}
        if outcome == "plans":
            time.sleep(30)  # let the words for the plans arrive
            doc = run.engine.read(run.cid)
            titles = {n["id"]: n["title"] for n in doc["needs"]}
            extra = {
                "needs": [{k: n[k] for k in ("title", "kind", "detail")} for n in doc["needs"]],
                "offers": [
                    {
                        "by": e["on_behalf_of"],
                        "need": titles[e["payload"]["target"]["id"]],
                        **e["payload"]["cost"],
                    }
                    for e in events(client, run.cid, "offer")
                ],
                "common": view_of(run.engine, run.cid, "p1")["common"],
                "plan_notes": view_of(run.engine, run.cid, "p1")["plan_notes"],
                "for_you": {
                    p: view_of(run.engine, run.cid, p)["mine"]["for_you"] for p in run.people
                },
            }
        run.report(outcome, extra)
        assert outcome == "plans", outcome


@pytest.mark.live
@pytest.mark.skipif(not KEY, reason="no key")
def test_gate_two_a_plan_is_made_a_sentence_changes_only_what_it_touches_and_the_room_ends(
    tmp_path: Path,
) -> None:
    with live_client(tmp_path) as client:
        run = Run(client, GOALS[1])
        cid, engine, c = run.cid, run.engine, client
        host = run.server.hosts[cid]
        run.to_plans()
        run.decide_and_commit()
        run.mark("committed")
        until(lambda: len(results_of(c, cid)) >= 3, 240, "three results")
        run.mark("results")
        after_results = len(run.server.store.read(cid))
        shown = view_of(engine, cid, "p1")
        said: dict[str, Any] = {}
        mine = next(t for t in shown["mine"]["tasks"] if t["can_mark_done"] or t["result"])
        until(lambda: view_of(engine, cid, "p1")["mine"]["tasks"][0]["can_mark_done"], 90, "done")
        said["done"] = c.post(
            "/v1/room/done",
            json={"task_id": mine["task_id"]},
            headers=bearer(run.people["p1"]["token"]),
        ).status_code
        token = run.people["p1"]["token"]
        said["private"] = c.post(
            "/v1/room/say", json={"text": "Is it far to walk there?"}, headers=bearer(token)
        ).json()
        said["room"] = c.post(
            "/v1/room/say",
            json={"text": "everyone: I will bring the chairs"},
            headers=bearer(token),
        ).json()
        titles = {n["id"]: n["title"] for n in engine.read(cid)["needs"]}
        other = next(
            (
                k
                for k, t in host.state.tasks.items()
                if t["assignee"] != "p1" and t["status"] == "committed"
            ),
            None,
        )
        before = {
            k: (t["status"], t["assignee"]) for k, t in host.state.tasks.items() if k != other
        }
        speaker = host.state.tasks[other]["assignee"] if other else "p1"
        sentence = (
            f"I can't do {titles[other].lower()} any more" if other else "Change the invitation"
        )
        said["change"] = c.post(
            "/v1/room/say", json={"text": sentence}, headers=bearer(run.people[speaker]["token"])
        ).json()
        until(lambda: not engine.read(cid)["change_pending"], 90, "the re-offers")
        until(lambda: len(events(c, cid, "propose")) >= 2, 120, "a plan for what changed")
        run.mark("replanned")
        view = view_of(engine, cid, "p1")
        change = view["change"]
        run.decide_and_commit()
        until(lambda: len(results_of(c, cid)) >= 4, 240, "the new result")
        run.mark("made_again")
        untouched = {
            k: (t["status"], t["assignee"]) for k, t in host.state.tasks.items() if k in before
        }
        extra = {
            "say": said,
            "change": change,
            "untouched_same": all(
                untouched[k] == before[k] for k in before if before[k][0] != "done"
            ),
            "results": [
                {
                    "kind": r["kind"],
                    "title": r["title"],
                    "by": r["by"],
                    "source": r["source"],
                    "data": r["data"],
                    "components": [n["component"] for n in r["tree"]],
                    "replaced_by": r["replaced_by"],
                }
                for r in view_of(engine, cid, "p1")["results"]
            ],
            "events_after_results": len(run.server.store.read(cid)) - after_results,
        }
        ended = c.post(
            "/v1/coalition/dissolve", json={"reason": "completed"}, headers=bearer(token)
        )
        extra["dissolve_status"] = ended.status_code
        extra["erased"] = all(engine.vault(cid, w) == {} for w in run.people)
        run.report("finished", extra)
        assert ended.status_code == 200 and extra["erased"]


@pytest.mark.live
@pytest.mark.skipif(not KEY, reason="no key")
def test_gate_two_the_deadline_ends_a_live_room(tmp_path: Path) -> None:
    with live_client(tmp_path) as client:
        run = Run(client, GOALS[1])
        run.to_plans()
        run.decide_and_commit()
        until(lambda: len(results_of(client, run.cid)) >= 1, 240, "a result")
        host = run.server.hosts[run.cid]
        stamp = host.state.charter["deadline"][:19]
        deadline = time.mktime(time.strptime(stamp, "%Y-%m-%dT%H:%M:%S"))
        run.engine.now = lambda: deadline + 7200
        until(lambda: host.state.stage == "Dissolve", 120, "the deadline to end the room")
        reason = events(client, run.cid, "dissolve")[0]["payload"]["reason"]
        until(lambda: run.engine.read(run.cid).get("final"), 30, "the results to be kept")
        erased = all(run.engine.vault(run.cid, w) == {} for w in run.people)
        run.report("deadline", {"dissolve_reason": reason, "erased": erased})
        assert reason == "deadline" and erased
