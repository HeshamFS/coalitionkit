# SPDX-License-Identifier: Apache-2.0
"""The host's side of delivery: send one envelope to a member's A2A endpoint and wait for it."""

from __future__ import annotations

import uuid
from typing import Any

import httpx
from a2a.client import Client, ClientCallContext, ClientConfig, create_client
from a2a.helpers.proto_helpers import get_message_text
from a2a.types import AgentCard, Message, Role, SendMessageRequest, Task, TaskState
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from coalitionkit_edges.a2a import EXTENSION_URI, CardKey, fetch_card, verify_card
from coalitionkit_edges.a2a.wire import envelope_part


class DeliveryError(Exception):
    """A member refused a delivery or did not answer it."""


class DeliveryClient:
    def __init__(self, card: AgentCard, client: Client, token: str) -> None:
        self.card = card
        self._client = client
        self._headers = {
            "A2A-Version": "1.0",
            "A2A-Extensions": EXTENSION_URI,
            "Authorization": f"Bearer {token}",
        }

    @classmethod
    async def connect(
        cls,
        http: httpx.AsyncClient,
        card_url: str,
        pinned_key: Ed25519PublicKey,
        pinned_kid: str,
        token: str,
    ) -> DeliveryClient:
        """Fetch the member's card, check it against the key pinned at join, open a client."""

        def check(card: AgentCard) -> None:
            verify_card(
                card, lambda kid: CardKey(pinned_kid, pinned_key) if kid == pinned_kid else None
            )

        card = await fetch_card(http, card_url, check)
        client = await create_client(card, ClientConfig(streaming=False, httpx_client=http))
        return cls(card, client, token)

    async def deliver(self, envelope: dict[str, Any]) -> str:
        """Send one envelope; return the member's reply text, or raise DeliveryError."""
        message = Message(
            message_id=str(uuid.uuid4()),
            context_id=str(envelope["coalition_id"]),
            role=Role.ROLE_USER,
            parts=[envelope_part(envelope)],
            extensions=[EXTENSION_URI],
        )
        context = ClientCallContext(service_parameters=self._headers)
        task: Task | None = None
        async for response in self._client.send_message(
            SendMessageRequest(message=message), context=context
        ):
            if response.HasField("task"):
                task = response.task
        if task is None:
            raise DeliveryError("the member answered with no task")
        text = get_message_text(task.status.message)
        if task.status.state != TaskState.TASK_STATE_COMPLETED:
            raise DeliveryError(f"{TaskState.Name(task.status.state)}: {text}")
        return text

    async def close(self) -> None:
        await self._client.close()
