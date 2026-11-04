# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
"""The Talk stage with the real model: three hosted seats talk before the plans.

Reads COALITIONKIT_META_API_KEY (and COALITIONKIT_BASETEN_API_KEY for the real Steward) from the
environment only. Run with ``COALITIONKIT_LIVE=1`` and ``-s``: the test prints one ``OUTCOME`` line
with the thread, the revised offers, the stops, and the time, tokens and cost of the talk.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import pytest
from room_flow import briefs_open
from room_rig import bearer, engine_of, events, join, server_of, sign, start_room, until, view_of
from test_room_live import REAL_STEWARD, answers_for, live_client

from coalitionkit_server.room.brief import given
from coalitionkit_server.room.talk import public_words
from coalitionkit_server.room.talk_rules import leaked, private_values

pytestmark = pytest.mark.live
KEY = bool(os.environ.get("COALITIONKIT_META_API_KEY")) and os.environ.get("COALITIONKIT_LIVE")
GOAL = (
    "Three of us need to organise a small get-together on the weekend: find a place, share "
    "the costs, buy the food and write a short invitation"
)
TALK_LABELS = {"Reading the talk and the offers", "Offering again on what changed"}


def talk_costs(doc: dict[str, Any]) -> dict[str, Any]:
    calls = [a for a in doc["activity"] if a["label"] in TALK_LABELS and a["ms"] is not None]
    return {
        "calls": len(calls),
        "ms": [a["ms"] for a in calls],
        "tokens": [sum(a.get("tokens", [0, 0])[i] for a in calls) for i in (0, 1)],
        "cost_usd": round(sum(a.get("cost") or 0 for a in calls) / 1e6, 5),
        "failed": [
            a.get("error")
            for a in doc["activity"]
            if a["label"] in TALK_LABELS and a["state"] == "failed"
        ],
    }


@pytest.mark.skipif(not KEY, reason="no key")
def test_three_hosted_seats_talk_before_the_plans(tmp_path: Path) -> None:
    with live_client(tmp_path) as client:
        server, engine = server_of(client), engine_of(client)
        room = start_room(client, seats=3, goal=GOAL, owner_name="Ada", real_steward=REAL_STEWARD)
        cid = room["coalition_id"]
        if REAL_STEWARD:
            ready = server.steward._ready  # pyright: ignore[reportPrivateUsage]
            until(lambda: ready is not None and ready.done(), 60, "the Steward")
        members = [join(client, room, name) for name in ("Ben", "Cleo")]
        people = {"p1": room["owner"], **{m["participant"]: m for m in members}}
        for who, person in people.items():
            sign(client, cid, person["token"], who)
        briefs_open(engine, cid, list(people), 180)
        slots = [s["id"] for s in engine.read(cid)["slots"]]
        for shift, (who, person) in enumerate(people.items()):
            questions = view_of(engine, cid, who)["mine"]["brief"]
            for question, value in answers_for(questions, slots, shift).items():
                reply = client.post(
                    "/v1/room/brief",
                    json={"question_id": question, "value": value},
                    headers=bearer(person["token"]),
                )
                assert reply.status_code == 200, reply.text
        until(lambda: engine.read(cid)["briefs_done"], 60, "the briefs")
        whisper = client.post(
            "/v1/room/say",
            json={"text": "Tell them I would rather not carry heavy things"},
            headers=bearer(members[1]["token"]),
        ).json()
        started = time.monotonic()
        until(lambda: engine.read(cid).get("talk_done") == "start", 400, "the talk")
        talked = round(time.monotonic() - started, 1)
        until(
            lambda: events(client, cid, "propose") or events(client, cid, "tension"), 240, "plans"
        )
        doc = engine.read(cid)
        said = events(client, cid, "say")
        leaks = {
            who: [
                e["payload"]["text"]
                for e in said
                if e["on_behalf_of"] == who
                and leaked(
                    e["payload"]["text"],
                    private_values(
                        given(engine, cid, who), public_words(server.hosts[cid].state, doc)
                    ),
                    "I would rather not carry heavy things"
                    if who == members[1]["participant"]
                    else "",
                )
            ]
            for who in people
        }
        offers_by_seq = [
            (e["seq"], e["on_behalf_of"], e["payload"]["offer_id"])
            for e in events(client, cid, "offer")
        ]
        first_say = min((e["seq"] for e in said), default=0)
        revised_events = [o for o in offers_by_seq if o[0] > first_say and first_say]
        plans = events(client, cid, "propose") + events(client, cid, "tension")
        outcome = {
            "whisper_route": whisper.get("route"),
            "seconds_in_talk": talked,
            "rounds": doc["talk"]["round"],
            "thread": [
                (
                    e["seq"],
                    e["on_behalf_of"],
                    e["payload"]["to"],
                    e["payload"]["intent"],
                    e["payload"]["text"],
                )
                for e in said
            ],
            "speakers": sorted({e["on_behalf_of"] for e in said}),
            "revised": doc.get("talk_revised", []),
            "offer_events_after_first_line": len(revised_events),
            "stops": [(s["policy"], s["seat"], s["explain"]) for s in doc["stops"]],
            "leaks": leaks,
            "plans_after_talk": min(e["seq"] for e in plans)
            > max((e["seq"] for e in said), default=0),
            "talk": talk_costs(doc),
            "real_steward": REAL_STEWARD,
        }
        print("OUTCOME " + json.dumps(outcome))
        assert len(said) >= 3 and len(outcome["speakers"]) >= 2, outcome["thread"]
        assert not any(leaks.values()), leaks
        assert outcome["plans_after_talk"]
