# SPDX-License-Identifier: Apache-2.0
"""The member side: send a signed envelope to a host over A2A and read the acknowledgement.

The host card is checked against a key pinned out of band (the invitation), never against a key
the card or a ``jku`` hands over.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx
from a2a.client import Client, ClientCallContext, ClientConfig, create_client
from a2a.types import AgentCard, Message, Role, SendMessageRequest, Task, TaskState
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from coalitionkit_contracts import (
    LogIntegrityError,
    SignatureError,
    check_receipts,
    validate_envelope,
    verify_envelope,
    verify_projection,
    verify_receipt,
)

from .identity import CardKey, fetch_card, verify_card
from .wire import EXTENSION_URI, envelope_part, envelope_parts

VERSION_HEADER = "A2A-Version"
EXTENSIONS_HEADER = "A2A-Extensions"


class EdgeCallError(Exception):
    """The call did not produce an acknowledgement or a host error."""


class ReceivedError(EdgeCallError):
    """The host answered with a ``coalition.error`` (host-signed, verified)."""

    def __init__(self, envelope: dict[str, Any]) -> None:
        payload: dict[str, Any] = envelope["payload"]
        super().__init__(f"host refused the envelope: {payload['code']}")
        self.envelope = envelope
        self.code: str = payload["code"]
        self.detail: dict[str, Any] = payload["detail"]
        self.ref: str = payload["ref"]


@dataclass(frozen=True)
class Ack:
    """The scope-filtered event (possibly absent) and its verified receipt."""

    accepted: dict[str, Any] | None
    receipt: dict[str, Any]
    task_id: str
    context_id: str


class MemberClient:
    """Talks to one host. Create it with :meth:`connect`."""

    def __init__(
        self,
        card: AgentCard,
        client: Client,
        host_key: Ed25519PublicKey,
        host_kid: str,
        headers: dict[str, str],
    ) -> None:
        self.host_card = card
        self._client = client
        self._host_key = host_key
        self._host_kid = host_kid
        self._headers = headers

    @classmethod
    async def connect(
        cls,
        http: httpx.AsyncClient,
        host_card_url: str,
        bearer_token: str,
        pinned_host_key: Ed25519PublicKey,
        pinned_kid: str,
    ) -> MemberClient:
        """Fetch the host card, verify it against the pinned key, and open an A2A client."""

        def lookup(kid: str) -> CardKey | None:
            return CardKey(pinned_kid, pinned_host_key) if kid == pinned_kid else None

        card = await fetch_card(http, host_card_url, lambda c: _check(c, lookup))
        client = await create_client(card, ClientConfig(streaming=False, httpx_client=http))
        headers = {
            VERSION_HEADER: "1.0",
            EXTENSIONS_HEADER: EXTENSION_URI,
            "Authorization": f"Bearer {bearer_token}",
        }
        return cls(card, client, pinned_host_key, pinned_kid, headers)

    async def send(
        self,
        envelope: dict[str, Any],
        *,
        addressable: frozenset[str] | None = None,
        validate: bool = True,
        headers: dict[str, str] | None = None,
    ) -> Ack:
        """Send one signed envelope; return its acknowledgement or raise ReceivedError.

        Before anything leaves the process the envelope is validated against its schemas (so no
        field a payload schema does not define is ever sent; ``validate=False`` is for tests of
        the host's own refusal) and, when ``addressable`` is given, its scope may name no
        participant outside it. ``headers`` replaces the default call headers (tests only).
        """
        if validate:
            validate_envelope(envelope)
        if addressable is not None:
            named: list[str] = list(envelope.get("scope", {}).get("participants") or [])
            outside = [p for p in named if p not in addressable]
            if outside:
                raise EdgeCallError(f"scope names participants it was not given: {outside}")
        message = Message(
            message_id=str(uuid.uuid4()),
            context_id=str(envelope["coalition_id"]),
            role=Role.ROLE_USER,
            parts=[envelope_part(envelope)],
            extensions=[EXTENSION_URI],
        )
        context = ClientCallContext(
            service_parameters=self._headers if headers is None else headers
        )
        task: Task | None = None
        async for response in self._client.send_message(
            SendMessageRequest(message=message), context=context
        ):
            if response.HasField("task"):
                task = response.task
        if task is None:
            raise EdgeCallError("the host answered with no task")
        return self._read(task)

    def _read(self, task: Task) -> Ack:
        found = envelope_parts(task.status.message.parts)
        state = task.status.state
        try:
            if state == TaskState.TASK_STATE_REJECTED and len(found) == 1:
                verify_envelope(found[0], self._host_key, expected_kid=self._host_kid)
                raise ReceivedError(found[0])
            if state == TaskState.TASK_STATE_COMPLETED and len(found) in {1, 2}:
                accepted = found[0] if len(found) == 2 else None
                receipt = found[-1]
                info = verify_receipt(receipt, self._host_key, expected_kid=self._host_kid)
                if accepted is not None:
                    if accepted.get("type") == "coalition.projection":
                        stub = verify_projection(
                            accepted, self._host_key, expected_kid=self._host_kid
                        )
                        if (
                            accepted.get("coalition_id") != receipt.get("coalition_id")
                            or stub.seq != info.seq
                        ):
                            raise LogIntegrityError(
                                "receipt_mismatch", "projection names another event"
                            )
                        check_receipts([stub], [info], self._host_key)
                    else:
                        verify_receipt(
                            receipt, self._host_key, accepted=accepted, expected_kid=self._host_kid
                        )
                return Ack(accepted, receipt, task.id, task.context_id)
        except (SignatureError, LogIntegrityError) as exc:
            raise EdgeCallError(f"the host's answer does not verify: {exc}") from exc
        raise EdgeCallError(
            f"unexpected task state {TaskState.Name(state)} with {len(found)} parts"
        )

    async def close(self) -> None:
        await self._client.close()


def _check(card: AgentCard, lookup: Callable[[str], CardKey | None]) -> None:
    verify_card(card, lookup)
