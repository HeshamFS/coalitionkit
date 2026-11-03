# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
"""A real room with the live model: the Gardener's needs and each seat's questions.

Reads COALITIONKIT_META_API_KEY from the environment only and skips without it. Run with ``-s``
to see the measured numbers and the model's own output.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from room_rig import bearer, engine_of, events, join, server_of, sign, start_room, until, view_of

from coalitionkit_server import Settings, create_server

GOAL = "Three of us need to prepare a short shared report: a plan, a budget and a review"


@pytest.mark.live
@pytest.mark.skipif(not os.environ.get("COALITIONKIT_META_API_KEY"), reason="no key")
def test_live_room_makes_needs_and_questions(tmp_path: Path) -> None:
    settings = Settings(
        store=SecretStr("sqlite:///" + str(tmp_path / "live.db")),
        host_key_file=tmp_path / "host.key",
        genesis="local",
        public_base_url="http://127.0.0.1:8000",
        room_engine="on",
    )
    with TestClient(
        create_server(settings),
        client=("127.0.0.1", 12345),
        headers={"Origin": settings.public_base_url},
    ) as client:
        server = server_of(client)
        engine = engine_of(client)
        room = start_room(client, seats=3, goal=GOAL)
        cid = room["coalition_id"]
        member = join(client, room)
        started = time.monotonic()
        sign(client, cid, room["owner"]["token"], "p1")
        sign(client, cid, member["token"], member["participant"])
        until(lambda: engine.read(cid)["needs_state"] == "ready", 90, "the Gardener's needs")
        needs_s = time.monotonic() - started
        until(lambda: len(events(client, cid, "need")) >= 2, 30, "needs seeded")
        done = client.post(
            "/v1/room/begin", json={"helpers": True}, headers=bearer(room["owner"]["token"])
        )
        assert done.status_code == 200, done.text
        who = ["p1", member["participant"]]
        until(lambda: all(engine.read(cid)["briefs"].get(p) for p in who), 120, "both briefs")
        brief_s = time.monotonic() - started - needs_s
        view = view_of(engine, cid, "p1")
        other = view_of(engine, cid, member["participant"])
        doc = engine.read(cid)
        records = [r for r in (server.gateway.meter.records if server.gateway.meter else [])]
        mine = [r for r in records if r.coalition_id == cid]
        print(
            json.dumps(
                {
                    "seconds_to_needs": round(needs_s, 1),
                    "seconds_for_briefs_and_begin": round(brief_s, 1),
                    "needs_source": doc["needs_source"],
                    "needs": [{k: n[k] for k in ("title", "kind", "detail")} for n in doc["needs"]],
                    "slots": [s["label"] for s in doc["slots"]],
                    "briefs": {
                        p: [
                            {k: q[k] for k in ("ask", "why", "component", "status")}
                            for q in view_of(engine, cid, p)["mine"]["brief"]
                        ]
                        for p in who
                    },
                    "calls": len(mine),
                    "prompt_tokens": sum(r.prompt_tokens for r in mine),
                    "completion_tokens": sum(r.completion_tokens for r in mine),
                    "cost_usd": sum(r.cost_micro_usd for r in mine) / 1_000_000,
                    "activity": [
                        {k: a[k] for k in ("verb", "label", "state", "ms", "source")}
                        for a in doc["activity"]
                    ],
                },
                indent=2,
            )
        )
        assert 2 <= len(doc["needs"]) <= 6 and doc["needs_source"] == "model"
        assert all(doc["briefs"][p]["source"] == "model" for p in who), doc["briefs"]
        for side in (view, other):
            assert 1 <= len(side["mine"]["brief"]) <= 3
            assert all(len(q["messages"]) == 3 for q in side["mine"]["brief"])
        assert mine and sum(r.cost_micro_usd for r in mine) > 0
