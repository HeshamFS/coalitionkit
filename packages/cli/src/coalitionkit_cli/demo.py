# SPDX-License-Identifier: Apache-2.0
"""Enroll local demo members before printing their viewer credentials."""

import asyncio
import json
from importlib.resources import files
from pathlib import Path

from coalitionkit_server.app import Server
from coalitionkit_server.genesis import enroll_member


async def enroll(server: Server, members: int) -> tuple[str, dict[str, str]]:
    charter = json.loads(
        files("coalitionkit_cli").joinpath("charter.json").read_text(encoding="utf-8")
    )
    charter["deciders"] = [f"p{i}" for i in range(1, members + 1)]
    created = server.create(charter)
    coalition = str(created["coalition_id"])
    tokens: dict[str, str] = {}
    for invite in created["invitations"]:
        redeemed = server.registry.redeem(invite["invitation"], server.ports, None, None)
        await enroll_member(server, redeemed)
        participant = str(redeemed["participant"])
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
