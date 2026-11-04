# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
"""The standing room: formed by the host, joined by visitors, ended by the clock, capped."""

from __future__ import annotations

import json
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from room_rig import NEEDS, RoomModel, gateway, server_of, until
from sets_rig import PACK, write_pack

from coalitionkit_contracts import public_key_to_jwk
from coalitionkit_server import Settings, create_server
from coalitionkit_server import standing as standing_module
from coalitionkit_server.room import budget, image
from coalitionkit_server.room.model import ask
from coalitionkit_server.standing import OWNER_FILE, StandingRoom, seat_roles

GOAL = "Strangers from anywhere build a one-hour tour together"


@contextmanager
def standing_host(
    tmp_path: Path, model: RoomModel, **extra: Any
) -> Generator[tuple[TestClient, StandingRoom]]:
    folder, key = write_pack(tmp_path)
    settings = Settings(
        store=SecretStr("sqlite:///" + str(tmp_path / "host.db")),
        host_key_file=tmp_path / "host.key",
        genesis="local",
        public_base_url="http://127.0.0.1:8000",
        room_engine="on",
        packs=[folder],
        pack_trusted_keys={"test-author": public_key_to_jwk(key.public_key(), "test-author")},
        standing_room_goal=GOAL,
        standing_room_pack=PACK,
        standing_room_seats=6,
        **extra,
    )
    app = create_server(settings, gateway(model))
    with TestClient(
        app, client=("127.0.0.1", 12345), headers={"Origin": settings.public_base_url}
    ) as http:
        standing = cast(FastAPI, http.app).state.standing
        assert isinstance(standing, StandingRoom)
        until(standing.current, what="the standing room to form")
        yield http, standing


def call(client: TestClient, fn: Any, *args: Any) -> Any:
    """Run ``fn`` on the app's own event loop, as the background clock would."""
    portal = client.portal
    assert portal is not None
    return portal.call(fn, *args)


@pytest.fixture(autouse=True)
def slow_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    # The test moves the clock itself; the background loop only forms the first room.
    monkeypatch.setattr(standing_module, "TICK_S", 3600.0)


def test_forms_bound_room_that_visitors_join_but_never_start(tmp_path: Path) -> None:
    with standing_host(tmp_path, RoomModel(needs=NEEDS)) as (client, standing):
        current = standing.current()
        assert current is not None
        coalition = current[0]
        server = server_of(client)
        assert server.hosts[coalition].state.charter["pack"] == {"name": PACK, "version": "1.0.0"}
        shown = client.get("/v1/standing").json()["room"]
        assert shown["goal"] == GOAL and shown["seats"] == 6 and shown["filled"] == 1
        assert shown["pack"] == PACK and 14 < shown["minutes_left"] <= 15
        owner = json.loads((tmp_path / OWNER_FILE).read_text(encoding="utf-8"))
        assert owner["coalition_id"] == coalition and owner["code"] == shown["code"]
        assert owner["token"] not in json.dumps(shown)
        joined = client.post("/v1/door/join", json={"code": shown["code"], "display_name": "Ana"})
        assert joined.status_code == 200, joined.text
        assert client.get("/v1/standing").json()["room"]["filled"] == 2
        # A visitor cannot start a room of their own, nor spend a model call drafting one.
        draft = {"goal": "Mine", "roles": [{"id": "member", "label": "m", "count": 2}]}
        body = {"draft": {**draft, "needs": [], "deadline": None}}
        start = client.post("/v1/genesis/start", json=body)
        assert start.status_code == 401
        assert client.post("/v1/genesis/draft", json={"goal": "Mine"}).status_code == 401


def test_ends_at_its_time_and_a_new_room_forms(tmp_path: Path) -> None:
    with standing_host(tmp_path, RoomModel(needs=NEEDS)) as (client, standing):
        first = standing.current()
        assert first is not None
        standing.now = lambda: datetime.now(UTC) + timedelta(minutes=16)
        call(client, standing.tick)
        server = server_of(client)
        assert server.hosts[first[0]].state.stage == "Dissolve"
        second = standing.current()
        assert second is not None and second[0] != first[0]
        owner = json.loads((tmp_path / OWNER_FILE).read_text(encoding="utf-8"))
        assert owner["coalition_id"] == second[0]


def test_begins_after_gathering_with_two_people(tmp_path: Path) -> None:
    model = RoomModel(needs=NEEDS)
    with standing_host(tmp_path, model, standing_room_gather_minutes=0) as (client, standing):
        current = standing.current()
        assert current is not None
        coalition = current[0]
        engine = server_of(client).room
        assert engine is not None
        call(client, standing.tick)  # the host's seat accepts its own charter
        until(lambda: engine.needs_ready(coalition), what="needs")
        call(client, standing.tick)
        assert not engine.read(coalition)["begun"]  # the host's seat alone does not begin
        code = client.get("/v1/standing").json()["room"]["code"]
        assert client.post("/v1/door/join", json={"code": code}).status_code == 200
        call(client, standing.tick)
        until(lambda: engine.read(coalition)["begun"], what="the room to begin")


def test_budget_refuses_model_calls_and_says_so(tmp_path: Path) -> None:
    model = RoomModel(needs=NEEDS)
    with standing_host(tmp_path, model, room_budget_usd=1e-9) as (client, standing):
        current = standing.current()
        assert current is not None
        coalition = current[0]
        engine = server_of(client).room
        assert engine is not None
        meter = server_of(client).gateway.meter
        assert meter is not None
        meter.record(coalition, "p1", "muse-spark-1.3", prompt_tokens=5000, completion_tokens=900)
        assert budget.spent_usd(engine, coalition) > 1e-9
        before = len(model.calls)
        schema = cast(Any, SimpleNamespace)

        async def question() -> object:
            return await ask(
                engine, coalition, "hosted_agent", "s", {}, schema, verb="asking", label="a q"
            )

        reply = call(client, question)
        assert reply is None and len(model.calls) == before
        picture = call(client, image.draw, engine, coalition, "p1", "a poster")
        assert picture == (None, budget.WHY)
        notes = [a["label"] for a in engine.read(coalition)["activity"]]
        assert sum("Model budget reached" in n for n in notes) == 1


def test_seat_roles_give_the_host_one_seat() -> None:
    def spec(*may: str) -> Any:
        return SimpleNamespace(may=list(may), label=None)

    pack = SimpleNamespace(
        manifest=SimpleNamespace(
            roles={"traveller": spec("offer", "decide"), "host": spec("charter", "offer")}
        )
    )
    roles = seat_roles(cast(Any, pack), 12)
    assert [(r.id, r.count) for r in roles] == [("host", 1), ("traveller", 11)]
    assert [(r.id, r.count) for r in seat_roles(None, 4)] == [("member", 4)]
