# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
"""Shared rig for the room engine tests: a real server with a scripted model."""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Generator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from coalitionkit_models import CostMeter, MissingKeyError, ModelGateway, load_price_table
from coalitionkit_models.gateway import ChatMessage, RawCompletion, Usage
from coalitionkit_models.settings import Route
from coalitionkit_models.settings import Settings as ModelSettings
from coalitionkit_runtime.steward import FakeSteward
from coalitionkit_server import Settings, create_server
from coalitionkit_server.adapter import Document
from coalitionkit_server.app import Server
from coalitionkit_server.room import RoomEngine
from coalitionkit_server.room.view import room_state

NEEDS: Document = {
    "needs": [
        {"title": "Find a venue", "kind": "place", "detail": "Somewhere all of us can reach."},
        {"title": "Share the costs", "kind": "budget", "detail": "Who pays what."},
        {"title": "Write the invitation", "kind": "draft", "detail": "A short note to send."},
    ],
    "slots": ["Saturday morning", "Saturday afternoon", "Sunday morning"],
}
BRIEF: Document = {
    "questions": [
        {
            "ask": "Which job would you take?",
            "why": "So your agent offers where you want to help.",
            "kind": "choice",
            "options": ["The venue", "The costs"],
            "low": 0,
            "high": 0,
            "step": 0,
            "unit": "",
        },
        {
            "ask": "How many hours could you give?",
            "why": "Offers stay inside it.",
            "kind": "amount",
            "options": [],
            "low": 0,
            "high": 10,
            "step": 1,
            "unit": "hours",
        },
        {
            "ask": "Which times suit you?",
            "why": "Only shared times are used.",
            "kind": "slots",
            "options": [],
            "low": 0,
            "high": 0,
            "step": 0,
            "unit": "",
        },
    ]
}

BRIEF_TEXT: Document = {
    "questions": [
        *BRIEF["questions"][:2],
        {
            "ask": "Anything we should know?",
            "why": "Your agent reads it before offering.",
            "kind": "text",
            "options": [],
            "low": 0,
            "high": 0,
            "step": 0,
            "unit": "",
        },
    ]
}


class RoomModel:
    """A scripted transport. ``None`` for a role means that role has no key."""

    def __init__(
        self,
        needs: Document | None = None,
        brief: Document | None = None,
        gardener_delay: float = 0.0,
        offers: Document | Callable[[str], Document] | None = None,
        names: Document | Callable[[str], Document] | None = None,
        foryou: Document | Callable[[str], Document] | None = None,
        offers_delay: float = 0.0,
    ) -> None:
        self.needs, self.brief, self.gardener_delay = needs, brief, gardener_delay
        self.offers, self.names, self.foryou = offers, names, foryou
        self.offers_delay = offers_delay
        self.calls: list[tuple[str, list[ChatMessage]]] = []

    @staticmethod
    def pick(reply: Document | Callable[[str], Document] | None, user: str) -> Document | None:
        return reply(user) if callable(reply) else reply

    async def create(
        self, route: Route, messages: Sequence[ChatMessage], opts: Mapping[str, Any]
    ) -> RawCompletion:
        import asyncio

        self.calls.append((route.role, list(messages)))
        system, user = str(messages[0]["content"]), str(messages[-1]["content"])
        reply: Document | None
        if route.role == "gardener":
            reply = self.pick(self.names, user) if "public name" in system else self.needs
            if self.gardener_delay and "public name" not in system:
                await asyncio.sleep(self.gardener_delay)
        elif route.role == "hosted_agent":
            if "An offer says" in system:
                reply = self.pick(self.offers, user)
                if self.offers_delay:
                    await asyncio.sleep(self.offers_delay)
            elif "means for them" in system:
                reply = self.pick(self.foryou, user)
            else:
                reply = self.brief
        else:
            reply = None
        if reply is None:
            raise MissingKeyError("no key in this test")
        return RawCompletion(json.dumps(reply), Usage(120, 60), "stop")


def gateway(model: RoomModel) -> ModelGateway:
    return ModelGateway(ModelSettings(), transport=model, meter=CostMeter(load_price_table()))


@contextmanager
def serve(tmp_path: Path, model: RoomModel, database: str = "host.db") -> Generator[TestClient]:
    settings = Settings(
        store=SecretStr("sqlite:///" + str(tmp_path / database)),
        host_key_file=tmp_path / "host.key",
        genesis="local",
        public_base_url="http://127.0.0.1:8000",
        room_engine="on",
    )
    app = create_server(settings, gateway(model))
    with TestClient(
        app, client=("127.0.0.1", 12345), headers={"Origin": settings.public_base_url}
    ) as http:
        yield http


def server_of(client: TestClient) -> Server:
    return cast(FastAPI, client.app).state.server


def engine_of(client: TestClient) -> RoomEngine:
    engine = server_of(client).room
    assert engine is not None
    return engine


def view_of(engine: RoomEngine, coalition: str, who: str) -> Document:
    view = room_state(engine, coalition, who)
    assert view is not None
    return view


def until(check: Callable[[], Any], seconds: float = 12.0, what: str = "condition") -> Any:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        found = check()
        if found:
            return found
        time.sleep(0.05)
    raise AssertionError(f"timed out waiting for {what}")


def start_room(
    client: TestClient,
    seats: int = 3,
    goal: str = "Three members need a shared room, a budget and an invitation tomorrow",
    steward: FakeSteward | None = None,
    owner_name: str | None = None,
) -> Document:
    server = server_of(client)
    draft = client.post("/v1/genesis/draft", json={"goal": goal}).json()["draft"]
    draft["roles"] = [{"id": "member", "label": "member", "count": seats}]
    draft["needs"] = []
    response = client.post(
        "/v1/genesis/start",
        json={"draft": draft, "owner_name": owner_name} if owner_name else {"draft": draft},
        headers={"Authorization": "Start " + server.registry.issue_start()},
    )
    assert response.status_code == 200, response.text
    created = response.json()
    server.hosts[created["coalition_id"]].steward = steward or FakeSteward()
    return created


def join(client: TestClient, room: Document, display_name: str | None = None) -> Document:
    owner = {"Authorization": "Bearer " + room["owner"]["token"]}
    invite = client.post("/v1/invitations", json={"kind": "member", "count": 1}, headers=owner)
    secret = invite.json()["invitations"][0]["link"].split("#")[1]
    body = {"invitation": secret, **({"display_name": display_name} if display_name else {})}
    response = client.post("/v1/invitations/accept", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def sign(client: TestClient, coalition: str, token: str, who: str) -> int:
    """Answer every open charter ask of ``who`` yes, as the web room would."""
    host = server_of(client).hosts[coalition]
    signed = 0
    for ask in host.open_consents(who):
        if ask["kind"] != "charter":
            continue
        response = client.post(
            "/v1/agent/answers",
            json={
                "interrupt_id": f"charter:{coalition}:{ask['revision']}:{who}",
                "consent": True,
            },
            headers={"Authorization": "Bearer " + token},
        )
        assert response.status_code == 200, response.text
        signed += 1
    return signed


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": "Bearer " + token}


def events(client: TestClient, coalition: str, kind: str) -> list[Document]:
    return [e for e in server_of(client).store.read(coalition) if e["type"] == "coalition." + kind]
