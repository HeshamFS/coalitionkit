# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false
"""Live: a real room bound to a pack that declares a compared set, with the real models.

Three hosted seats answer their agents' questions and the pack's set question; the room crosses
the set by PSI, publishes only the shared values, each person sees their own private count, and a
made ``list`` names only shared values. Reads COALITIONKIT_META_API_KEY (and the Baseten key for
the real Steward) from the environment only. Run with ``-s`` for the ``OUTCOME`` line.
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
from room_flow import briefs_open
from room_rig import bearer, engine_of, events, server_of, until, view_of
from sets_rig import pack_room, write_pack
from test_room_live import KEY, REAL_STEWARD, Run, answers_for, results_of

from coalitionkit_contracts import public_key_to_jwk
from coalitionkit_server import Settings, create_server
from coalitionkit_server.adapter import Document
from coalitionkit_server.room import sets

pytestmark = pytest.mark.live

OPTIONS = ["white", "grey", "sage green", "sky blue", "sunny yellow"]
COMPARE = f"""compare:
  - id: colours
    label: Colours everyone likes
    question:
      text: "Which of these wall colours would you be happy with?"
      kind: choice
      options: {json.dumps(OPTIONS)}
"""
PICKS = [
    ["white", "sage green", "sky blue"],
    ["sage green", "sky blue", "sunny yellow"],
    ["grey", "sage green", "sky blue"],
]
GOAL = os.environ.get(
    "SETS_LIVE_GOAL",
    "Three of us are repainting the shared kitchen this weekend: pick the wall colour together, "
    "make a list of what each of us brings, and write a short note to the neighbours",
)


def live_pack_client(tmp_path: Path) -> TestClient:
    folder, key = write_pack(tmp_path, COMPARE)
    settings = Settings(
        store=SecretStr("sqlite:///" + str(tmp_path / "live.db")),
        host_key_file=tmp_path / "host.key",
        genesis="local",
        public_base_url="http://127.0.0.1:8000",
        room_engine="on",
        packs=[folder],
        pack_trusted_keys={"test-author": public_key_to_jwk(key.public_key(), "test-author")},
    )
    return TestClient(
        create_server(settings),
        client=("127.0.0.1", 12345),
        headers={"Origin": settings.public_base_url},
    )


def answer_all(run: Run, people: dict[str, Document]) -> None:
    slots = [s["id"] for s in run.engine.read(run.cid)["slots"]]
    for shift, (who, person) in enumerate(people.items()):
        questions = view_of(run.engine, run.cid, who)["mine"]["brief"]
        own = [q for q in questions if not q["id"].startswith(sets.QUESTION_PREFIX)]
        said = answers_for(own, slots, shift)
        said["set-colours"] = [f"o{OPTIONS.index(c) + 1}" for c in PICKS[shift]]
        for question, value in said.items():
            reply = run.client.post(
                "/v1/room/brief",
                json={"question_id": question, "value": value},
                headers=bearer(person["token"]),
            )
            assert reply.status_code == 200, (question, value, reply.text)


class SetsRun(Run):
    """The live run of ``test_room_live``, in a room bound to the sets pack."""

    def __init__(self, client: TestClient) -> None:  # pyright: ignore[reportMissingSuperCall]
        self.client, self.goal = client, GOAL
        self.server, self.engine = server_of(client), engine_of(client)
        self.started, self.marks = time.monotonic(), {}
        if REAL_STEWARD:
            ready = self.server.steward._ready  # pyright: ignore[reportPrivateUsage]
            until(lambda: ready is not None and ready.done(), 60, "the Steward")
        self.room, members = pack_room(
            client, real_steward=REAL_STEWARD, goal=GOAL, needs=2, seconds=90
        )
        self.cid = self.room["coalition_id"]
        self.people = {"p1": self.room["owner"], **{m["participant"]: m for m in members}}


def test_a_real_room_compares_a_pack_set_and_makes_a_list_from_the_shared_values(
    tmp_path: Path,
) -> None:
    if not KEY:
        pytest.skip("no key")
    with live_pack_client(tmp_path) as client:
        run = SetsRun(client)
        cid, engine = run.cid, run.engine
        briefs_open(engine, cid, list(run.people), 180)
        run.mark("briefs_open")
        answer_all(run, run.people)
        until(lambda: (engine.read(cid)["compare"] or {}).get("state") == "done", 240, "compare")
        run.mark("compared")
        found = [
            json.loads(e["payload"]["content"])
            for e in events(client, cid, "observe")
            if '"set": "colours"' in e["payload"]["content"]
        ]
        until(lambda: events(client, cid, "propose"), 240, "plans")
        run.mark("plans")
        run.decide_and_commit()
        until(lambda: len(results_of(client, cid)) >= 2, 300, "results")
        run.mark("results")
        made = view_of(engine, cid, "p1")["results"]
        lists = [r for r in made if r["kind"] == "list"]
        text = json.dumps([r["data"] for r in lists]).lower()
        named = [c for c in OPTIONS if c in text]
        extra: dict[str, Any] = {
            "published": found,
            "mine": {w: view_of(engine, cid, w)["mine"]["sets"] for w in run.people},
            "needs": [(n["title"], n["kind"]) for n in engine.read(cid)["needs"]],
            "results": [(r["kind"], r["title"], r["source"], r["data"]) for r in made],
            "colours_named_in_lists": named,
        }
        run.report("sets", extra)
        assert found == [
            {"common": 1, "set": "colours", "values": ["sage green", "sky blue"], "compared": 3}
        ]
        assert extra["mine"] == {w: {"colours": 1} for w in run.people}
        assert set(named) <= {"sage green", "sky blue"}, named
