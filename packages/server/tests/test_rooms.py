# SPDX-License-Identifier: Apache-2.0
"""The first screen's room listing: empty by default, and always marked when it holds samples."""

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError

from coalitionkit_server import Settings, create_server
from coalitionkit_server.rooms import load_rooms

ROOM = {
    "id": "r1",
    "goal": "Goal one",
    "seats": 4,
    "filled": 1,
    "closes": "closes soon",
    "lat": 1.0,
    "lon": 2.0,
}


def client_for(tmp_path: Path, **extra: object) -> Iterator[TestClient]:
    settings = Settings(
        store=SecretStr(f"sqlite:///{tmp_path / 'host.db'}"),
        host_key_file=tmp_path / "host.key",
        genesis="local",
        **extra,  # type: ignore[arg-type]
    )
    with TestClient(
        create_server(settings),
        client=("127.0.0.1", 1000),
        headers={"Origin": settings.public_base_url},
    ) as client:
        yield client


@pytest.fixture
def plain(tmp_path: Path) -> Iterator[TestClient]:
    yield from client_for(tmp_path)


def test_a_host_without_a_file_lists_nothing(plain: TestClient) -> None:
    assert plain.get("/v1/rooms").json() == {"rooms": [], "examples": []}


def test_a_cross_site_request_is_refused(plain: TestClient) -> None:
    assert plain.get("/v1/rooms", headers={"Origin": "http://other"}).status_code == 403


def test_every_listed_room_is_marked_as_a_sample(tmp_path: Path) -> None:
    path = tmp_path / "rooms.json"
    path.write_text(json.dumps({"rooms": [ROOM], "examples": ["Say this"]}), encoding="utf-8")
    for client in client_for(tmp_path, sample_rooms=path):
        body = client.get("/v1/rooms").json()
        assert body["examples"] == ["Say this"]
        assert body["rooms"] == [{**ROOM, "status": "forming", "sample": True}]


@pytest.mark.parametrize(
    "bad",
    [
        {**ROOM, "filled": 9},
        {**ROOM, "lat": 200},
        {**ROOM, "sample": False},
        {**ROOM, "secret": "x"},
    ],
)
def test_a_bad_file_stops_the_host_at_start(tmp_path: Path, bad: dict[str, object]) -> None:
    path = tmp_path / "rooms.json"
    path.write_text(json.dumps({"rooms": [bad]}), encoding="utf-8")
    with pytest.raises(ValidationError):
        load_rooms(path)
