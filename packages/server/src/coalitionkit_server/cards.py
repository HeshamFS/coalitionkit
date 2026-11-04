# SPDX-License-Identifier: Apache-2.0
"""Signed discovery document for a participant hosted by this process."""

from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coalitionkit_edges.a2a.identity import card_key_entry, coalition_extension, sign_card


def member_card(
    base: str,
    key: Ed25519PrivateKey,
    name: str = "CoalitionKit member",
    description: str = "A hosted Coalition participant",
) -> AgentCard:
    card = AgentCard(
        name=name,
        description=description,
        version="0.1.0",
        supported_interfaces=[
            AgentInterface(url=base + "/a2a", protocol_binding="JSONRPC", protocol_version="1.0")
        ],
        capabilities=AgentCapabilities(
            extensions=[
                coalition_extension(
                    {
                        "roles": ["member"],
                        "surfaces": ["mcp_app", "web"],
                        "vault": "hosted",
                        "keys": [card_key_entry(key.public_key(), "agent")],
                    },
                    "Participates in Coalitions",
                )
            ]
        ),
        default_input_modes=["application/vnd.coalitionkit.envelope+json"],
        default_output_modes=["application/vnd.coalitionkit.envelope+json"],
        skills=[
            AgentSkill(
                id="member",
                name="Coalition member",
                description="Represents one participant",
                tags=["coalition"],
            )
        ],
    )
    return sign_card(card, key, "agent")
