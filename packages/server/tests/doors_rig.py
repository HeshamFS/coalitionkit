# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
"""A real coalitionkit-server on localhost for the doors end-to-end test (apps/web/e2e).

Run as a script. It enrolls four participants in one Coalition, prints one JSON line when ready
(base URL, Coalition ID, one bearer token per participant) and then reads one JSON command per
line on stdin and answers each with one JSON line:

- ``{"op": "emit", "as": "p1", "content": "...", "audience": "coalition" | ["organizer"]}``
  submits a signed ``coalition.observe`` as that participant, for everyone or for the holders of
  the listed roles, and answers once the host has accepted it, with ``accepted_ms`` (wall clock,
  milliseconds since the epoch, taken the moment the acknowledgement came back).
- ``{"op": "quit"}`` stops the server.

It writes nothing outside a temporary directory and uses no model.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import httpx
from pydantic import SecretStr
from test_server import CHARTER, Running

from coalitionkit_contracts import public_key_to_jwk, sign_owner_proof
from coalitionkit_edges.a2a import MemberClient
from coalitionkit_mcp.gateway import build_envelope
from coalitionkit_server import Settings

PEOPLE = {
    "p1": ["member", "organizer"],
    "p2": ["member"],
    "p3": ["member"],
    "p4": ["member", "observer"],
}
ADMIN = "Bearer admin-doors"


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def join_envelope(running: Running, coalition: str, participant: str, roles: list[str]) -> Any:
    person = running.state.registry.hosted_for(coalition, participant)
    jwk = public_key_to_jwk(person.owner_key.public_key(), person.owner_kid)
    body = {
        "card_url": person.card_url,
        "owner_key": jwk,
        "owner_proof": sign_owner_proof(
            coalition, participant, person.card_url, jwk, person.owner_key
        ),
        "roles_requested": roles,
        "surfaces": ["web"],
        "vault": "hosted",
    }
    return build_envelope(
        person, coalition, "coalition.join", body, scope={"audience": "coalition"}
    )


def enroll(running: Running) -> tuple[str, dict[str, str]]:
    charter = {
        **CHARTER,
        "roles": [{"id": "member"}, {"id": "organizer"}, {"id": "observer"}],
        "deciders": list(PEOPLE),
    }
    with httpx.Client(base_url=running.base) as http:
        created = http.post("/admin/coalitions", json=charter, headers={"Authorization": ADMIN})
        created.raise_for_status()
        info = created.json()
        tokens: dict[str, str] = {}
        for invite in info["invitations"]:
            redeemed = http.post("/invitations/redeem", json={"invitation": invite["invitation"]})
            redeemed.raise_for_status()
            tokens[redeemed.json()["participant"]] = redeemed.json()["token"]
    return info["coalition_id"], tokens


async def open_clients(
    running: Running, http: httpx.AsyncClient, tokens: dict[str, str]
) -> dict[str, MemberClient]:
    clients: dict[str, MemberClient] = {}
    for name, token in tokens.items():
        clients[name] = await MemberClient.connect(
            http, running.state.signer.card_url, token, running.state.key.public_key(), "host"
        )
    return clients


def scope_of(audience: Any) -> dict[str, Any]:
    if audience == "coalition":
        return {"audience": "coalition"}
    # Role scopes need no consent from named people, so the keyless Steward lets them through.
    return {"audience": "roles", "roles": list(audience)}


async def serve(running: Running, coalition: str, clients: dict[str, MemberClient]) -> None:
    loop = asyncio.get_running_loop()
    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line:
            return
        command = json.loads(line)
        if command["op"] == "quit":
            return
        person = running.state.registry.hosted_for(coalition, command["as"])
        event = build_envelope(
            person,
            coalition,
            "coalition.observe",
            {"source": "chat", "content": command["content"]},
            scope=scope_of(command["audience"]),
        )
        await clients[command["as"]].send(event)
        accepted_ms = time.time() * 1000
        print(json.dumps({"ok": True, "accepted_ms": accepted_ms}), flush=True)


async def main() -> None:
    logging.disable(logging.INFO)  # stdout carries only the JSON lines below
    with tempfile.TemporaryDirectory() as tmp:
        port = int(os.environ.get("DOORS_RIG_PORT") or free_port())
        settings = Settings(
            store=SecretStr(f"sqlite:///{Path(tmp) / 'host.db'}"),
            host_key_file=Path(tmp) / "keys" / "host.key",
            bind_port=port,
            public_base_url=f"http://127.0.0.1:{port}",
            admin_token=SecretStr("admin-doors"),
        )
        with Running(settings) as running:
            coalition, tokens = enroll(running)
            async with httpx.AsyncClient(timeout=20) as http:
                clients = await open_clients(running, http, tokens)
                for name, roles in PEOPLE.items():
                    await clients[name].send(join_envelope(running, coalition, name, roles))
                ready = {"ready": True, "base": running.base, "coalition": coalition}
                print(json.dumps({**ready, "tokens": tokens}), flush=True)
                try:
                    await serve(running, coalition, clients)
                finally:
                    for client in clients.values():
                        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
