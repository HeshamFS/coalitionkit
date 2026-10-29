# SPDX-License-Identifier: Apache-2.0
"""One scenario over the real A2A edge: members talk to the host through a local port."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coalitionkit_edges.a2a import (
    CredentialRegistry,
    HostSigner,
    MemberClient,
    ReceivedError,
    create_host_app,
)
from coalitionkit_edges.a2a.server import build_host_card
from coalitionkit_edges.a2a.testing import RunningServer, free_port
from coalitionkit_runtime import SQLiteStore
from coalitionkit_server import HostPort

from .arena import Arena, Participant
from .metrics import Recorder
from .watch import check_log

NAMES = ("ana", "ben", "cho")


@dataclass(frozen=True)
class WireResult:
    acknowledged: int
    refused_codes: list[str]
    plan_decided: bool
    metrics: dict[str, Any]


async def run_wire() -> WireResult:
    recorder = Recorder("wire")
    port_number = free_port()
    base = f"http://127.0.0.1:{port_number}"
    host_key = Ed25519PrivateKey.generate()
    arena = Arena.open(
        SQLiteStore(),
        deciders=["ana", "ben"],
        host_key=host_key,
        card_url=f"{base}/.well-known/agent-card.json",
    )
    host = arena.host
    signer = HostSigner(host.card_url, host_key, host.kid)
    port = HostPort(host)
    credentials = CredentialRegistry()
    people: dict[str, Participant] = {}
    for name in NAMES:
        person = Participant(host, name)
        people[name] = person
        arena.members[name] = person
        card = build_host_card(HostSigner(person.auth.card_url, person.agent, person.name), base)
        port.invite(name, person.auth.card_url, card)
        credentials.add(f"token-{name}", person.auth.card_url)
    app = create_host_app(port, signer, credentials, base)
    refused: list[str] = []
    acknowledged = 0
    with RunningServer(app, port_number):
        async with httpx.AsyncClient() as http:
            clients = {
                name: await MemberClient.connect(
                    http, signer.card_url, f"token-{name}", host_key.public_key(), host.kid
                )
                for name in NAMES
            }

            async def send(name: str, envelope: dict[str, Any]) -> bool:
                nonlocal acknowledged
                started = time.perf_counter()
                try:
                    await clients[name].send(envelope)
                except ReceivedError as error:
                    refused.append(error.code)
                    return False
                finally:
                    recorder.sample("call_s", time.perf_counter() - started)
                acknowledged += 1
                return True

            for name in NAMES:
                assert await send(name, people[name].envelope("join", people[name].join_body()))
            revision = host.state.charter["revision"]
            for name in NAMES:
                envelope = people[name].decision_envelope("charter", host.coalition_id, revision)
                assert await send(name, envelope)
            task = arena.need()
            for name in NAMES:
                assert await send(name, people[name].offer_envelope(task, 30, 5))
            (plan,) = arena.propose({task: "cho"})
            for name in ("ana", "ben"):
                assert await send(name, people[name].decision_envelope("plan", plan))
            # A second answer for the same revision is refused over the wire, not accepted twice.
            await send("ana", people["ana"].decision_envelope("plan", plan))
            for client in clients.values():
                await client.close()
    events = check_log(host)
    recorder.count("events", events)
    recorder.count("member_calls_acknowledged", acknowledged)
    stored = sum(1 for e in arena.events() if e["on_behalf_of"] != "host")
    recorder.count("lost_events", acknowledged - stored)
    recorder.count("member_calls_refused", len(refused))
    decided = host.state.subject("plan", plan)["status"] == "decided"
    arena.close()
    return WireResult(acknowledged, refused, decided, recorder.result())
