# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false
"""Live: a real room with real models records its agents' model calls as ``coalition.tool``.

Reads COALITIONKIT_META_API_KEY (and COALITIONKIT_BASETEN_API_KEY for the Steward) from the
environment only, and runs only with COALITIONKIT_LIVE=1. Run with ``-s`` for the OUTCOME line.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from room_flow import briefs_open
from room_rig import bearer, engine_of, events, join, server_of, sign, start_room, until
from test_room_live import answers_for, live_client

from coalitionkit_server.room.view import room_state

pytestmark = pytest.mark.live
KEY = (
    bool(os.environ.get("COALITIONKIT_META_API_KEY")) and os.environ.get("COALITIONKIT_LIVE") == "1"
)
GOAL = "Two of us need to organise a small get-together: pick a time and share the costs"


@pytest.mark.skipif(not KEY, reason="no key")
def test_a_live_room_shows_its_model_calls(tmp_path: Path) -> None:
    with live_client(tmp_path) as client:
        room = start_room(client, seats=2, goal=GOAL, real_steward=True)
        cid, engine = room["coalition_id"], engine_of(client)
        sign(client, cid, room["owner"]["token"], "p1")
        member = join(client, room)
        sign(client, cid, member["token"], member["participant"])
        people = {"p1": room["owner"]["token"], member["participant"]: member["token"]}
        briefs_open(engine, cid, list(people), 120)
        slots = [s["id"] for s in engine.read(cid)["slots"]]
        for shift, (who, token) in enumerate(people.items()):
            asked = (room_state(engine, cid, who) or {})["mine"]["brief"]
            for qid, value in answers_for(asked, slots, shift).items():
                client.post(
                    "/v1/room/brief",
                    json={"question_id": qid, "value": value},
                    headers=bearer(token),
                )
        until(lambda: (engine.read(cid)["compare"] or {}).get("state") == "done", 240, "compare")
        tools = [e["payload"] for e in events(client, cid, "tool")]
        finished = [t for t in tools if t["tool"].startswith("model:") and t["status"] == "done"]
        meter = server_of(client).cost_meter(cid)
        print(
            "OUTCOME",
            json.dumps(
                {
                    "tool_events": len(tools),
                    "model_calls": [(t["seat"], t["tool"], t["ms"], t["result"]) for t in finished],
                    "steward_reviews": sum(t["tool"] == "steward:review" for t in tools),
                    "psi": [t["result"] for t in tools if t["tool"] == "psi:compare"],
                    "cost": meter,
                }
            ),
        )
        names = {t["tool"] for t in finished}
        assert {"model:needs", "model:brief"} <= names, names
        assert all(t["ms"] > 0 and "tokens" in t["result"] for t in finished if t["ms"])
        assert any(t["tool"] == "steward:review" for t in tools)
