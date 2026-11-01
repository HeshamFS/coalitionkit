# SPDX-License-Identifier: Apache-2.0
import asyncio
import json
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from test_bound_pack_runtime import accepted, decide
from test_genesis import server_for
from test_pack_genesis import pack_client

from coalitionkit_mcp.gateway import build_envelope
from coalitionkit_mcp.ports import HostedParticipant
from coalitionkit_runtime import CoalitionHost
from coalitionkit_runtime.steward import FakeSteward
from coalitionkit_server.adapter import Document
from coalitionkit_server.app import Server
from coalitionkit_server.genesis import enroll_member
from coalitionkit_surfaces.frames import encode

__all__ = ["pack_client"]


def setup(client: TestClient) -> tuple[Server, CoalitionHost, HostedParticipant, Document]:
    server = server_for(client)
    key = next(iter(server.packs))
    pack = server.packs[key]
    server.packs[key] = replace(
        pack,
        schemas={
            **pack.schemas,
            "offer": {
                "type": "object",
                "properties": {
                    "required_value": {"type": "string"},
                    "secret": {"x-private": True},
                },
                "required": ["required_value"],
            },
        },
    )
    created = server.create(
        {
            "goal": "Agree",
            "roles": [{"id": "coordinator"}],
            "rules": [],
            "deadline": "2099-01-01T00:00:00Z",
            "deciders": ["p1"],
            "pack": {"name": key[0], "version": key[1]},
        }
    )
    cid = created["coalition_id"]
    for name in ("p1", "p2"):
        redeemed = server.registry.redeem(
            server.registry.issue(cid, name), server.ports, None, None
        )
        asyncio.run(enroll_member(server, redeemed, "coordinator"))
    host = server.hosts[cid]
    decide(host, server.registry.hosted_for(cid, "p1"))
    # A host need is valid in the open charter's planning stage.
    result = host.host_emit(
        "need",
        {
            "description": "Task",
            "requirements": [],
            "window": {"start": "2026-11-01T00:00:00Z", "end": "2099-01-01T00:00:00Z"},
            "ext": {"item_kind": "item"},
        },
        {"audience": "coalition"},
    )
    task = accepted(result)["payload"]["need_id"]
    person = server.registry.hosted_for(cid, "p1")
    body = {
        "offer_id": "offer",
        "target": {"kind": "need", "id": task},
        "capacity": 1,
        "cost": {"minutes": 1, "money": 0, "effort": "low"},
        "valid_until": "2099-01-01T00:00:00Z",
    }
    return server, host, person, body


def submit(
    server: Server, host: CoalitionHost, person: HostedParticipant, body: Document
) -> Document:
    return asyncio.run(
        server.accept(
            build_envelope(
                person, host.coalition_id, "coalition.offer", body, scope={"audience": "coalition"}
            ),
            person.card_url,
        )
    )


def test_protocol_private_extension(pack_client: TestClient) -> None:
    server, host, person, body = setup(pack_client)
    steward = FakeSteward()
    host.steward = steward
    before = server.store.read(host.coalition_id)
    reply = submit(
        server,
        host,
        person,
        {**body, "ext": {"required_value": "ok", "secret": "PRIVATE-PROTOCOL-CANARY"}},
    )
    assert reply["error"]["code"] == "schema_invalid"
    assert server.store.read(host.coalition_id) == before
    hub = server.surfaces[host.coalition_id].state.hub
    for viewer in ("p1", "p2", "steward"):
        surfaces: list[object] = [host.view(viewer), host.replay(viewer)]
        for session in (hub.agent_session(viewer), hub.feed_session(viewer)):
            surfaces.extend(encode(f) for f in session.start())
        assert "PRIVATE-PROTOCOL-CANARY" not in json.dumps(surfaces)
    assert steward.calls == []


@pytest.mark.parametrize("extra", [{}, {"ext": {}}])
def test_required_extension(pack_client: TestClient, extra: Document) -> None:
    server, host, person, body = setup(pack_client)
    reply = submit(server, host, person, {**body, **extra})
    assert reply["error"]["code"] == "schema_invalid"


def test_initial_charter_policy(pack_client: TestClient) -> None:
    server = server_for(pack_client)
    key = next(iter(server.packs))
    pack = server.packs[key]
    policy = pack.policies[0].model_copy(
        update={"applies_to": ["coalition.charter"], "then": "block"}
    )
    server.packs[key] = replace(pack, policies=(policy,))
    with pytest.raises(ValueError, match="pack_violation"):
        server.create(
            {
                "goal": "unreviewed",
                "roles": [{"id": "coordinator"}],
                "rules": [],
                "deadline": "2099-01-01T00:00:00Z",
                "deciders": ["p1"],
                "pack": {"name": key[0], "version": key[1]},
            }
        )
    assert all(not server.store.read(cid) for cid in server.hosts)


def test_escalation_reaches_owner(pack_client: TestClient) -> None:
    server, host, person, body = setup(pack_client)
    reply = submit(server, host, person, {**body, "ext": {"required_value": "unreviewed"}})
    assert reply["error"]["code"] == "steward_blocked"
    hub = server.surfaces[host.coalition_id].state.hub
    policy = next(iter(server.packs.values())).policies[0]
    own = "".join(encode(f) for f in hub.agent_session("p1").start())
    assert policy.id in own and policy.explain in own and "revise and resend" in own
    for viewer in ("p2", "steward"):
        for session in (hub.agent_session(viewer), hub.feed_session(viewer)):
            assert policy.explain not in "".join(encode(f) for f in session.start())
