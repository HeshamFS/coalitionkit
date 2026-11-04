# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
"""A host open to the public cannot spend without limit: rooms a day, and a budget per room."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import SecretStr
from room_rig import RoomModel, gateway, server_of

from coalitionkit_server import Settings, create_server

GOAL = "Three members need a shared room, a budget and an invitation tomorrow"


def limited(tmp_path: Path, **limits: object) -> TestClient:
    settings = Settings(
        store=SecretStr("sqlite:///" + str(tmp_path / "host.db")),
        host_key_file=tmp_path / "host.key",
        genesis="local",
        public_base_url="http://127.0.0.1:8000",
        room_engine="on",
        **limits,  # pyright: ignore[reportArgumentType]
    )
    return TestClient(
        create_server(settings, gateway(RoomModel())),
        client=("127.0.0.1", 12345),
        headers={"Origin": settings.public_base_url},
    )


def draft(client: TestClient) -> object:
    return client.post("/v1/genesis/draft", json={"goal": GOAL})


def test_rooms_stop_starting_when_the_days_count_is_used(tmp_path: Path) -> None:
    with limited(tmp_path, rooms_per_day=1) as client:
        plan = draft(client).json()["draft"]  # pyright: ignore[reportAttributeAccessIssue]
        assert client.post("/v1/genesis/start", json={"draft": plan}).status_code == 200
        refused = client.post("/v1/genesis/start", json={"draft": plan})
    assert refused.status_code == 429
    assert "for today" in refused.json()["detail"]


def test_the_model_stops_reading_sentences_when_the_days_count_is_used(tmp_path: Path) -> None:
    with limited(tmp_path, rooms_per_day=1) as client:
        answers = [draft(client).status_code for _ in range(11)]  # pyright: ignore[reportAttributeAccessIssue]
    assert answers == [200] * 10 + [429]


def test_a_room_gets_its_budget(tmp_path: Path) -> None:
    with limited(tmp_path, room_budget_usd=0.5) as client:
        plan = draft(client).json()["draft"]  # pyright: ignore[reportAttributeAccessIssue]
        room = client.post("/v1/genesis/start", json={"draft": plan}).json()
        meter = server_of(client).gateway.meter
        assert meter is not None
        assert meter._limits[room["coalition_id"]] == 500_000  # pyright: ignore[reportPrivateUsage]


def test_a_host_without_limits_is_not_limited(tmp_path: Path) -> None:
    with limited(tmp_path) as client:
        assert [draft(client).status_code for _ in range(12)] == [200] * 12  # pyright: ignore[reportAttributeAccessIssue]
