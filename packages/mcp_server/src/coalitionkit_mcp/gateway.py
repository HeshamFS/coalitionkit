# SPDX-License-Identifier: Apache-2.0
"""Builds a signed Coalition envelope for a participant and hands it to the host."""

from __future__ import annotations

from typing import Any, cast

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from coalitionkit_contracts import (
    LogIntegrityError,
    SchemaValidationError,
    SignatureError,
    new_ulid,
    sign_envelope,
    validate_envelope,
    validate_payload,
    verify_receipt,
)
from coalitionkit_edges.a2a.host_port import HostPort

from .errors import CoalitionToolError
from .ports import HostedParticipant

#: Everything this server sends is for the host to derive from; it never widens a scope itself.
HOST_SCOPE: dict[str, Any] = {"audience": "host"}


def build_envelope(
    hosted: HostedParticipant,
    coalition_id: str,
    message_type: str,
    payload: dict[str, Any],
    *,
    scope: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """An envelope from ``hosted`` signed with its own agent key. No other key is ever used."""
    envelope: dict[str, Any] = {
        "ext_version": "0.1",
        "coalition_id": coalition_id,
        "event_id": new_ulid(),
        "type": message_type,
        "sender": hosted.card_url,
        "on_behalf_of": hosted.participant,
        "scope": dict(HOST_SCOPE if scope is None else scope),
        "payload": payload,
    }
    envelope["sig"] = sign_envelope(envelope, hosted.agent_key, hosted.agent_kid)
    return envelope


async def send(
    host: HostPort,
    hosted: HostedParticipant,
    coalition_id: str,
    message_type: str,
    payload: dict[str, Any],
    *,
    scope: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Submit an envelope and return its acknowledgement metadata or accepted envelope.

    Raises CoalitionToolError with the host's ``coalition.error`` code when it refuses.
    """
    try:
        validate_payload(message_type, payload)
    except SchemaValidationError as exc:
        raise CoalitionToolError("schema_invalid", "; ".join(exc.errors)[:500]) from exc
    envelope = build_envelope(hosted, coalition_id, message_type, payload, scope=scope)
    reply = await host.accept(envelope, hosted.card_url)
    error: Any = reply.get("error")
    if isinstance(error, dict):
        detail: Any = error.get("detail")  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]
        message = detail.get("message", "") if isinstance(detail, dict) else ""  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]
        raise CoalitionToolError(str(error.get("code", "not_authorized")), str(message))  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
    accepted: Any = reply.get("accepted")
    if accepted is None:
        return receipt_ack(host, reply.get("receipt"), envelope)
    if not isinstance(accepted, dict):
        raise CoalitionToolError("not_authorized", "the host gave no acknowledgement")
    return {k: v for k, v in accepted.items()}  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]


def receipt_ack(host: HostPort, receipt: Any, submitted: dict[str, Any]) -> dict[str, Any]:
    """Verify a receipt against locally configured trust, never a key from the reply.

    Remote ports expose ``host_public_key``. In-process adapters may instead expose
    their host or signer, whose configured key supplies the same trust anchor.
    """
    key = getattr(host, "host_public_key", None)
    if key is None:
        local = getattr(host, "host", None) or getattr(host, "signer", None)
        private = getattr(local, "private_key", None)
        if private is not None:
            key = private.public_key()
    if not isinstance(key, Ed25519PublicKey):
        raise CoalitionToolError("bad_signature", "no pinned host key for receipt")
    try:
        if not isinstance(receipt, dict):
            raise ValueError("missing receipt")
        data = cast(dict[str, Any], receipt)
        validate_envelope(data)
        info = verify_receipt(data, key)
        if data["coalition_id"] != submitted["coalition_id"]:
            raise ValueError("wrong coalition")
    except SchemaValidationError, SignatureError, LogIntegrityError, ValueError:
        raise CoalitionToolError("bad_signature", "invalid host receipt") from None
    return {"event_id": submitted["event_id"], "seq": info.seq}
