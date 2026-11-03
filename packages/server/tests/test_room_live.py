# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
"""Gate 1: a real room with the live model, driven only through the web routes.

An owner, one more person and a helper sign, begin, brief, offer, compare and reach real plans
with no demo script. Reads COALITIONKIT_META_API_KEY from the environment only and skips without
it. Run with ``-s`` to see the measured numbers and everything the model wrote.
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
from room_rig import bearer, engine_of, events, join, server_of, sign, start_room, until, view_of

from coalitionkit_server import Settings, create_server
from coalitionkit_server.adapter import Document

GOAL = "Two of us need to prepare a short shared report: a plan, a budget and a review"


def answers_for(questions: list[Document], slots: list[str], shift: int) -> dict[str, Any]:
    """What a plain person would tell their agent: first option, half the range, some times."""
    said: dict[str, Any] = {}
    for q in questions:
        kind = q["component"]
        first = next(m for m in q["messages"] if "updateComponents" in m)
        field = next(c for c in first["updateComponents"]["components"] if c["id"] == "input")
        if kind == "Slider":
            said[q["id"]] = (field["min"]["value"] + field["max"]["value"]) // 4 or 1
        elif kind == "TextArea":
            said[q["id"]] = "Afternoons suit me better than mornings."
        elif field.get("multiple"):
            said[q["id"]] = slots[shift : shift + 3]
        else:
            said[q["id"]] = field["options"][0]["id"]
    return said


@pytest.mark.live
@pytest.mark.skipif(not os.environ.get("COALITIONKIT_META_API_KEY"), reason="no key")
def test_gate_one_a_real_room_reaches_real_plans(tmp_path: Path) -> None:
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
        cid, owner = room["coalition_id"], room["owner"]
        member = join(client, room)
        who = ["p1", member["participant"]]
        marks: dict[str, float] = {}
        started = time.monotonic()
        try:
            sign(client, cid, owner["token"], "p1")
            sign(client, cid, member["token"], member["participant"])
            until(lambda: len(events(client, cid, "need")) >= 2, 90, "needs seeded")
            marks["needs_seeded"] = time.monotonic() - started
            begun = client.post(
                "/v1/room/begin", json={"helpers": True}, headers=bearer(owner["token"])
            )
            assert begun.status_code == 200, begun.text
            sign(client, cid, member["token"], member["participant"])
            briefs_open(engine, cid, who, 90)
            marks["briefs_open_after_begin"] = time.monotonic() - started
            slots = [s["id"] for s in engine.read(cid)["slots"]]
            for shift, (person, token) in enumerate(
                ((who[0], owner["token"]), (who[1], member["token"]))
            ):
                questions = view_of(engine, cid, person)["mine"]["brief"]
                for question, value in answers_for(questions, slots, shift).items():
                    reply = client.post(
                        "/v1/room/brief",
                        json={"question_id": question, "value": value},
                        headers=bearer(token),
                    )
                    assert reply.status_code == 200, (question, value, reply.text)
            until(lambda: events(client, cid, "propose"), 180, "real plans")
            marks["plans"] = time.monotonic() - started
            until(lambda: len(engine.read(cid)["plan_notes"]) >= 1, 90, "plan names")
            until(
                lambda: all(view_of(engine, cid, p)["mine"]["for_you"] for p in who), 90, "for you"
            )
            marks["plan_words"] = time.monotonic() - started
        finally:
            shown = show(server, engine, client, cid, who, marks)
        proposals = events(client, cid, "propose")
        assert proposals and all(p["payload"]["plans"] for p in proposals)
        assert "helper-1" in {o["by"] for o in shown["offers"]}
        assert set(shown["plan_notes"]) == {
            p["plan_id"] for e in proposals for p in e["payload"]["plans"]
        }
        assert shown["cost_usd"] > 0


def show(
    server: Any, engine: Any, client: Any, cid: str, who: list[str], marks: dict[str, float]
) -> dict[str, Any]:
    meter = server.gateway.meter
    assert meter is not None
    records = [r for r in meter.records if r.coalition_id == cid]
    doc = engine.read(cid)
    titles = {n["id"]: n["title"] for n in doc["needs"]}
    offers = [
        {
            "by": e["on_behalf_of"],
            "need": titles[e["payload"]["target"]["id"]],
            **e["payload"]["cost"],
        }
        for e in events(client, cid, "offer")
    ]
    view = view_of(engine, cid, "p1")
    shown: dict[str, Any] = {
        "seconds": {k: round(v, 1) for k, v in marks.items()},
        "model_calls": len(records),
        "prompt_tokens": sum(r.prompt_tokens for r in records),
        "completion_tokens": sum(r.completion_tokens for r in records),
        "cost_usd": sum(r.cost_micro_usd for r in records) / 1_000_000,
        "needs": [{k: n[k] for k in ("title", "kind", "detail")} for n in doc["needs"]],
        "offers": offers,
        "common": view["common"],
        "plan_notes": view["plan_notes"],
        "for_you": {p: view_of(engine, cid, p)["mine"]["for_you"] for p in who},
        "feed": {p: [x["text"] for x in view_of(engine, cid, p)["mine"]["feed"]] for p in who},
        "activity": [
            {k: a[k] for k in ("verb", "label", "state", "ms", "source")} for a in view["activity"]
        ],
        "failed_calls": [
            {"label": a["label"], "error": a.get("error")}
            for a in engine.read(cid)["activity"]
            if a["state"] == "failed"
        ],
    }
    print(json.dumps(shown, indent=2))
    return shown
