# SPDX-License-Identifier: Apache-2.0
"""Signed discovery metadata and explicit local lifecycle operations."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from google.protobuf.json_format import MessageToDict

from coalitionkit_contracts import jwk_to_public_key
from coalitionkit_edges.a2a.identity import (
    CardRegistry,
    card_key_entry,
    coalition_extension,
    sign_card,
)

from .artifact import VERSION, connect, load, verify_consent
from .catalog import twin_data
from .process import Sandbox
from .prove import AttackResult
from .schema import Config, DeviceConfig


def tool_names(config: Config) -> list[str]:
    if isinstance(config, DeviceConfig):
        return [*("read_" + field.id for field in config.fields), "status", "alarm"]
    return ["list_free_slots", "hold_slot", "confirm", "cancel"]


def publish(folder: Path, sandbox: Sandbox, config: Config) -> None:
    _, manifest, manifest_hash = load(folder)
    key = Ed25519PrivateKey.generate()
    tools = tool_names(config)
    card = AgentCard(
        name=config.name,
        description="Owner-approved fixed-template MCP agent",
        version=VERSION,
        supported_interfaces=[
            AgentInterface(url=sandbox.url, protocol_binding="MCP", protocol_version="2026-07-28")
        ],
        capabilities=AgentCapabilities(
            extensions=[
                coalition_extension(
                    {
                        "roles": [],
                        "keys": [card_key_entry(key.public_key(), "agent")],
                        "owner": manifest["owner"],
                        "owner_id": manifest["owner_id"],
                        "manifest_hash": manifest_hash,
                    },
                    "Mint artifact; Coalition membership is not implemented",
                )
            ]
        ),
        default_input_modes=["application/json"],
        default_output_modes=["application/json"],
        skills=[
            AgentSkill(id=name, name=name, description="Fixed template operation", tags=["mint"])
            for name in tools
        ],
    )
    signed = sign_card(card, key, "agent")
    CardRegistry("mint").admit(sandbox.url, signed)
    (folder / "agent-card.json").write_text(
        json.dumps(MessageToDict(signed)), encoding="utf-8", newline="\n"
    )
    skill = (
        "---\nname: minted-agent\ndescription: Use the approved fixed-template tools.\n---\n\n"
        f"Endpoint: {sandbox.url}\n\nManifest: {manifest_hash}\n\n"
        "Owner approval is required. Confirm and cancel require an owner signature over "
        "the exact operation and manifest. Device tools never write.\n\n"
        + "\n".join(f"- `{name}`" for name in tools)
        + "\n"
    )
    (folder / "SKILL.md").write_text(skill, encoding="utf-8", newline="\n")


@dataclass
class Minted:
    folder: Path
    sandbox: Sandbox
    manifest_hash: str
    attacks: list[AttackResult]
    elapsed_seconds: float
    cost_micro_usd: int
    tokens: int

    def approve(self, signature: str) -> None:
        _, manifest, current = load(self.folder)
        if current != self.manifest_hash or not all(a.passed for a in self.attacks):
            raise ValueError("approval does not match proven manifest")
        verify_consent(jwk_to_public_key(manifest["owner"]), current, "approve", {}, signature)
        with connect(self.folder) as db:
            state = db.execute("SELECT state FROM lifecycle").fetchone()[0]
            if state != "pending":
                raise ValueError("only pending artifacts may be approved")
            db.execute("UPDATE lifecycle SET state='approved', proof=?", (signature,))

    def pause(self) -> None:
        with connect(self.folder) as db:
            db.execute("UPDATE lifecycle SET state='paused', proof=NULL")

    def delete(self) -> None:
        load(self.folder)
        with connect(self.folder) as db:
            db.execute("UPDATE lifecycle SET state='deleted', proof=NULL")
        self.close()
        expected = {
            "config.json",
            "manifest.json",
            "store.sqlite",
            "worker.log",
            "agent-card.json",
            "SKILL.md",
        }
        files = list(self.folder.iterdir())
        if self.folder.is_symlink() or any(
            path.name not in expected or path.is_symlink() or not path.is_file() for path in files
        ):
            raise ValueError("unexpected artifact contents; stopped but not removed")
        for path in files:
            path.unlink()
        self.folder.rmdir()

    def close(self) -> None:
        self.sandbox.stop()

    def scorecard(self) -> dict[str, Any]:
        return {
            "manifest_hash": self.manifest_hash,
            "elapsed_seconds": self.elapsed_seconds,
            "cost_micro_usd": self.cost_micro_usd,
            "tokens": self.tokens,
            "attacks": [asdict(a) for a in self.attacks],
            "passed": self.elapsed_seconds < 90 and all(a.passed for a in self.attacks),
        }

    def catalog_data(self) -> dict[str, Any]:
        config, manifest, _ = load(self.folder)
        with connect(self.folder) as db:
            state = db.execute("SELECT state FROM lifecycle").fetchone()[0]
        return {
            **twin_data(self.folder, config, manifest["artifact_id"]),
            "MintPipeline": {
                "cost": str(self.cost_micro_usd),
                "elapsed": self.elapsed_seconds,
                "stages": [{"name": "publish", "state": state}],
            },
            "AttackTests": {"tests": [asdict(a) for a in self.attacks]},
            "PublishApproval": {
                "coalitions": [],
                "tests": self.scorecard(),
                "spec": {
                    "reads": tool_names(config)
                    if isinstance(config, DeviceConfig)
                    else ["list_free_slots"],
                    "acts": []
                    if isinstance(config, DeviceConfig)
                    else [
                        {"tool": name, "bounds": config.model_dump()}
                        for name in ("hold_slot", "confirm", "cancel")
                    ],
                    "never": ["execute model output"],
                },
            },
            "MintedAgentCard": {
                "agent": {
                    "name": config.name,
                    "version": VERSION,
                    "runtime": "local",
                    "owner": manifest["owner_id"],
                },
                "health": state,
                "readings": [],
                "tools": tool_names(config),
            },
        }
