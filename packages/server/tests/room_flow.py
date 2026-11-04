# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
"""Helpers for driving a whole room through the web routes in tests."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
from room_rig import bearer, events, join, server_of, sign, start_room, until

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


def sign_kind(client: TestClient, coalition: str, token: str, who: str, kind: str) -> int:
    """Answer yes to every open ask of this kind, as the person would on the trusted card."""
    host = server_of(client).hosts[coalition]
    signed = 0
    for ask in host.open_consents(who):
        if ask["kind"] != kind:
            continue
        response = client.post(
            "/v1/agent/answers",
            json={
                "interrupt_id": f"{kind}:{ask['id']}:{ask['revision']}:{who}",
                "consent": True,
                **({"choice": ask["choice"]} if "choice" in ask else {}),
            },
            headers=bearer(token),
        )
        assert response.status_code == 200, response.text
        signed += 1
    return signed


def decide_plan(client: TestClient, coalition: str, people: dict[str, Document]) -> None:
    """Everyone asked says yes to the plan: the tension's first option, or the plan itself."""
    host = server_of(client).hosts[coalition]
    for who, person in people.items():
        asks = host.open_consents(who)
        if any(a["kind"] == "tension_option" for a in asks):
            asks = [a for a in asks if a["kind"] == "tension_option"]
        else:  # saying yes to one plan supersedes the others of its set
            asks = [a for a in asks if a["kind"] == "plan"][:1]
        for ask in asks:
            if ask["kind"] == "tension_option":
                tension = next(
                    e
                    for e in events(client, coalition, "tension")
                    if e["payload"]["tension_id"] == ask["id"]
                )
                choice = tension["payload"]["options"][0]["option_id"]
                body = {
                    "interrupt_id": f"tension_option:{ask['id']}:{ask['revision']}:{who}",
                    "consent": True,
                    "choice": choice,
                }
            elif ask["kind"] == "plan":
                body = {
                    "interrupt_id": f"plan:{ask['id']}:{ask['revision']}:{who}",
                    "consent": True,
                }
            else:
                continue
            response = client.post("/v1/agent/answers", json=body, headers=bearer(person["token"]))
            assert response.status_code == 200, response.text


def briefs_open(engine: Any, coalition: str, people: list[str], seconds: float = 12.0) -> None:
    until(
        lambda: all(engine.read(coalition)["briefs"].get(p) for p in people),
        seconds,
        "every brief to open",
    )
