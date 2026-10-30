# SPDX-License-Identifier: Apache-2.0
"""Enroll local demo members before printing their viewer credentials."""

import asyncio
import json
from pathlib import Path

from coalitionkit_contracts import public_key_to_jwk, sign_owner_proof
from coalitionkit_mcp.gateway import build_envelope
from coalitionkit_server.app import Server


async def enroll(server: Server, members: int) -> tuple[str, dict[str, str]]:
    charter = json.loads(Path(__file__).with_name("charter.json").read_text())
    charter["deciders"] = [f"p{i}" for i in range(1, members + 1)]
    created = server.create(charter)
    coalition = str(created["coalition_id"])
    tokens: dict[str, str] = {}
    for invite in created["invitations"]:
        redeemed = server.registry.redeem(invite["invitation"], server.ports, None, None)
        participant = str(redeemed["participant"])
        person = server.registry.hosted_for(coalition, participant)
        jwk = public_key_to_jwk(person.owner_key.public_key(), person.owner_kid)
        envelope = build_envelope(
            person,
            coalition,
            "coalition.join",
            {
                "card_url": person.card_url,
                "owner_key": jwk,
                "owner_proof": sign_owner_proof(
                    coalition, participant, person.card_url, jwk, person.owner_key
                ),
                "roles_requested": ["member"],
                "surfaces": ["web"],
                "vault": "hosted",
            },
            scope={"audience": "coalition"},
        )
        reply = await server.accept(envelope, person.card_url)
        if "error" in reply:
            raise ValueError(f"demo join refused for {participant}: {reply['error']['code']}")
        tokens[participant] = str(redeemed["token"])
    return coalition, tokens


def demo_start(server: Server, data: Path, members: int, base: str) -> None:
    marker = data / "demo-coalition"
    if marker.exists():
        print(f"Coalition: {marker.read_text(encoding='utf-8')} (demo, created earlier)")
        print("Reuse the Viewer tokens shown on the first run; --reset starts afresh.")
        return
    coalition, tokens = asyncio.run(enroll(server, members))
    marker.write_text(coalition, encoding="utf-8")
    print(f"Coalition: {coalition}", flush=True)
    for participant, token in tokens.items():
        print(f"Sign in: {participant} {base}/ Viewer token: {token}", flush=True)
