# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false
"""A LangChain seat and a LangGraph seat in one real room, each on a real model.

A black box: a real `coalitionkit up` process, a person acting through the routes a browser uses,
and two seats that know the room only from their tools. Prints an ``OUTCOME`` line. Needs
COALITIONKIT_LIVE=1, COALITIONKIT_META_API_KEY and COALITIONKIT_BASETEN_API_KEY.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[3]
GOAL = (
    "Three of us need to organise a small get-together: find a place, share the costs, and "
    "write a short invitation to send out"
)
KEYS = ("COALITIONKIT_META_API_KEY", "COALITIONKIT_BASETEN_API_KEY")
READY = all(os.environ.get(k) for k in KEYS) and os.environ.get("COALITIONKIT_LIVE") == "1"
EXE = Path(sys.executable).with_name("coalitionkit.exe" if os.name == "nt" else "coalitionkit")


def seats_example() -> Any:
    spec = importlib.util.spec_from_file_location(
        "framework_seats", ROOT / "examples/rooms/framework_seats.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


class Person:
    """The room's opener, doing only what the browser can do."""

    def __init__(self, base: str, log: Any) -> None:
        self.http = httpx.Client(base_url=base, headers={"Origin": base}, timeout=120)
        self.log = log
        self.token, self.who, self.coalition, self.code = "", "p1", "", ""

    def open_room(self) -> None:
        draft = self.http.post("/v1/genesis/draft", json={"goal": GOAL}).raise_for_status().json()
        plan = draft["draft"]
        plan["roles"] = [{"id": "member", "label": "member", "count": 3}]
        room = (
            self.http.post("/v1/genesis/start", json={"draft": plan, "owner_name": "Mira"})
            .raise_for_status()
            .json()
        )
        self.token, self.who = room["owner"]["token"], room["owner"]["participant"]
        self.coalition, self.code = room["coalition_id"], room["door"]["code"]

    def state(self) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "text/event-stream"}
        with self.http.stream("GET", "/v1/feed", headers=headers) as reply:
            for line in reply.iter_lines():
                if line.startswith("data:"):
                    event = json.loads(line[5:])
                    if event.get("type") == "STATE_SNAPSHOT":
                        return event["snapshot"]
        return {}

    def answer(self, ask: dict[str, Any], choice: str | None = None) -> None:
        body: dict[str, Any] = {
            "interrupt_id": f"{ask['kind']}:{ask['id']}:{ask['revision']}:{self.who}",
            "consent": True,
            **({"choice": choice} if choice else {}),
        }
        reply = self.http.post(
            "/v1/agent/answers", json=body, headers={"Authorization": f"Bearer {self.token}"}
        )
        self.log(f"[person] {ask['kind']} yes -> {reply.status_code}")

    def step(self, state: dict[str, Any]) -> None:
        auth = {"Authorization": f"Bearer {self.token}"}
        mine = (state.get("room") or {}).get("mine") or {}
        for question in mine.get("brief", []):
            if question["status"] == "open":
                body = {"question_id": question["id"], "skip": True}
                self.http.post("/v1/room/brief", json=body, headers=auth)
        asks = mine.get("asks") or []
        events = (state.get("events") or {}).values()
        votes = [a for a in asks if a["kind"] == "tension_option"]
        for ask in votes:
            tension = next(
                e["payload"] for e in events if e["payload"].get("tension_id") == ask["id"]
            )
            self.answer(ask, tension["options"][0]["option_id"])
        if not votes:
            said = [
                e["payload"]["subject"]["id"]
                for e in events
                if e["type"] == "coalition.decide"
                and e["payload"]["subject"]["kind"] == "plan"
                and e["payload"].get("consent")
            ]
            plans = [a for a in asks if a["kind"] == "plan"]
            chosen = next((a for a in plans if a["id"] in said), plans[0] if plans else None)
            if chosen:
                self.answer(chosen)
        for ask in asks:
            if ask["kind"] in {"charter", "commitment", "task"}:
                self.answer(ask)
        for task in mine.get("tasks", []):
            if task.get("can_mark_done"):
                self.http.post("/v1/room/done", json={"task_id": task["task_id"]}, headers=auth)

    def run(self, stop: threading.Event, seconds: float) -> dict[str, Any]:
        end, state = time.monotonic() + seconds, {}
        while time.monotonic() < end and not stop.is_set():
            state = self.state()
            needs = (state.get("room") or {}).get("needs") or []
            if needs and all(n["status"] == "done" for n in needs):
                self.log("[person] every need is done")
                break
            try:
                self.step(state)
            except (httpx.HTTPError, StopIteration, KeyError) as error:
                self.log(f"[person] {type(error).__name__}: {str(error)[:120]}")
            time.sleep(4)
        return state


def summary(state: dict[str, Any], used: dict[str, Any]) -> dict[str, Any]:
    events = list((state.get("events") or {}).values())
    room = state.get("room") or {}
    by = lambda kind, who: [  # noqa: E731
        e for e in events if e["type"] == f"coalition.{kind}" and e.get("on_behalf_of") == who
    ]
    assigned = {
        a["assignee"]
        for e in events
        if e["type"] == "coalition.propose"
        for p in e["payload"].get("plans", [])
        for a in p.get("assignments", [])
    }
    return {
        "phase": room.get("phase"),
        "offers": {who: len(by("offer", who)) for who in ("p2", "p3")},
        "signed": {who: len(by("decide", who)) for who in ("p2", "p3")},
        "done_reports": {who: len(by("done", who)) for who in ("p2", "p3")},
        "seen_in_plans": sorted(assigned),
        "needs": [(n["title"], n["status"], n["assignee"]) for n in room.get("needs", [])],
        "host_cost": state.get("cost_meter"),
        "tokens": {
            model: {k: u.get(k) for k in ("input_tokens", "output_tokens", "total_tokens")}
            for model, u in used.items()
        },
    }


@pytest.mark.live
@pytest.mark.skipif(not READY, reason="needs COALITIONKIT_LIVE=1 and both model keys")
def test_both_seats_join_one_real_room_and_their_offers_are_accepted(tmp_path: Path) -> None:
    lines: list[str] = []
    started = time.monotonic()

    def log(line: str) -> None:
        text = f"{time.monotonic() - started:7.1f} {line}"
        lines.append(text)
        print(text[:300], flush=True)

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    host = subprocess.Popen(
        [EXE, "up", "--no-web", "--port", str(port), "--data-dir", str(tmp_path / "data")],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(240):
            try:
                if httpx.get(base + "/healthz", timeout=1).status_code == 200:
                    break
            except httpx.TransportError:
                time.sleep(0.5)
        person = Person(base, log)
        person.open_room()
        log("[person] the room is open")
        seconds = float(os.environ.get("SEATS_LIVE_SECONDS", "1500"))
        stop = threading.Event()
        used: dict[str, Any] = {}

        def seats() -> None:
            used.update(asyncio.run(seats_example().both_seats(base, person.code, log, seconds)))

        thread = threading.Thread(target=seats, daemon=True)
        thread.start()
        state = person.run(stop, seconds)
        outcome = summary(person.state() or state, used)
        reply = person.http.post(
            "/v1/coalition/dissolve",
            json={"reason": "completed"},
            headers={"Authorization": f"Bearer {person.token}"},
        )
        log(f"[person] ended the room -> {reply.status_code}")
        thread.join(90)
        outcome["tokens"] = {
            model: {k: u.get(k) for k in ("input_tokens", "output_tokens", "total_tokens")}
            for model, u in used.items()
        }
        print("OUTCOME " + json.dumps(outcome), flush=True)
    finally:
        host.terminate()
        host.wait(30)
    assert outcome["offers"]["p2"] >= 1, "the LangChain seat made no offer the room accepted"
    assert outcome["offers"]["p3"] >= 1, "the LangGraph seat made no offer the room accepted"
    assert outcome["signed"]["p2"] >= 1 and outcome["signed"]["p3"] >= 1
    # Who holds what is the proof their offers entered the plan: the opener's own view of a plan
    # shows only the opener's part.
    assert {"p2", "p3"} & {need[2] for need in outcome["needs"]}, "no plan used their offers"
