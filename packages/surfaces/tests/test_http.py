# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient
from surfaces_support import World

from coalitionkit_surfaces import SurfaceHub, create_app


@pytest.fixture
def client(hub: SurfaceHub) -> TestClient:
    return TestClient(create_app(hub))


def auth(name: str) -> dict[str, str]:
    return {"Authorization": f"Bearer tok-{name}"}


def events(text: str) -> list[dict[str, Any]]:
    return [json.loads(c[len("data: ") :]) for c in text.split("\n\n") if c.startswith("data: ")]


def test_endpoints_need_a_valid_viewer_token(client: TestClient) -> None:
    for path in ("/v1/feed", "/v1/agent"):
        assert client.get(path).status_code == 401
        assert client.get(path, headers={"Authorization": "Bearer nope"}).status_code == 401
    body = {"interrupt_id": "plan:x:1:alice", "consent": True}
    assert client.post("/v1/agent/answers", json=body).status_code == 401


def test_feed_stream_starts_with_run_then_the_viewers_snapshot(
    client: TestClient, world: World
) -> None:
    world.need(scope={"audience": "participants", "participants": ["alice"]})
    seen: dict[str, list[dict[str, Any]]] = {}
    for name in ("alice", "carol"):
        response = client.get("/v1/feed", headers=auth(name))
        assert response.headers["content-type"].startswith("text/event-stream")
        seen[name] = events(response.text)
    assert [e["type"] for e in seen["alice"][:2]] == ["RUN_STARTED", "STATE_SNAPSHOT"]
    assert len(seen["alice"][1]["snapshot"]["events"]) > len(seen["carol"][1]["snapshot"]["events"])


def test_agent_stream_and_answer_endpoint(client: TestClient, world: World) -> None:
    plan = world.propose(world.need(), ["alice"])
    interrupt = f"plan:{plan}:1:alice"
    stream = events(client.get("/v1/agent", headers=auth("alice")).text)
    assert stream[-1]["type"] == "RUN_FINISHED" and stream[-1]["outcome"]["type"] == "interrupt"
    assert stream[-1]["outcome"]["interrupts"][0]["id"] == interrupt
    refused = client.post(
        "/v1/agent/answers", headers=auth("bob"), json={"interrupt_id": interrupt, "consent": True}
    )
    assert refused.status_code == 403 and refused.json()["error"] == "not_your_request"
    done = client.post(
        "/v1/agent/answers",
        headers=auth("alice"),
        json={"interrupt_id": interrupt, "consent": True},
    )
    assert done.status_code == 200 and done.json()["status"] == "accepted"
    again = client.post(
        "/v1/agent/answers",
        headers=auth("alice"),
        json={"interrupt_id": interrupt, "consent": True},
    )
    assert again.status_code == 409 and again.json()["error"] == "not_open"
    assert client.post("/v1/agent/answers", headers=auth("alice"), json={}).status_code == 422
