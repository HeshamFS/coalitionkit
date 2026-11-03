# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
"""Helpers for driving a whole room through the web routes in tests."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
from room_rig import bearer, events, join, sign, start_room, until

from coalitionkit_runtime.steward import FakeSteward
from coalitionkit_server.adapter import Document


def full_room(
    client: TestClient, seats: int = 3, steward: FakeSteward | None = None
) -> tuple[Document, list[Document]]:
    """A room whose every seat has signed: it begins by itself. Returns the owner and members."""
    room = start_room(client, seats=seats, steward=steward)
    cid = room["coalition_id"]
    sign(client, cid, room["owner"]["token"], "p1")
    members = [join(client, room) for _ in range(seats - 1)]
    for member in members:
        sign(client, cid, member["token"], member["participant"])
    until(lambda: len(events(client, cid, "need")) >= 3, what="needs")
    return room, members


def reply_brief(client: TestClient, token: str, answers: dict[str, Any]) -> None:
    """Answer (or, for ``None``, skip) each question of this seat's brief."""
    for question, value in answers.items():
        body = {"question_id": question, **({"skip": True} if value is None else {"value": value})}
        response = client.post("/v1/room/brief", json=body, headers=bearer(token))
        assert response.status_code == 200, response.text


def offers_by(client: TestClient, coalition: str, who: str) -> list[Document]:
    return [e for e in events(client, coalition, "offer") if e["on_behalf_of"] == who]


def briefs_open(engine: Any, coalition: str, people: list[str]) -> None:
    until(
        lambda: all(engine.read(coalition)["briefs"].get(p) for p in people),
        what="every brief to open",
    )
