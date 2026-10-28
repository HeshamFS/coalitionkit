# SPDX-License-Identifier: Apache-2.0
"""The port the edge calls into the host, a signer for host-originated envelopes, and a fake host.

``HostPort.accept`` returns one of two shapes:

* ``{"accepted": <envelope with seq, ts, prev_hash>, "receipt": <host-signed coalition.receipt>}``
* ``{"error": <coalition.error payload {code, detail, ref}>}``, which the edge wraps in a
  host-signed ``coalition.error`` envelope addressed to the sender.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coalitionkit_contracts import (
    SchemaValidationError,
    is_ulid,
    new_ulid,
    prev_hash,
    receipt_payload,
    sign_envelope,
    validate_envelope,
)


class HostPort(Protocol):
    """What the A2A edge needs from the host."""

    async def accept(
        self, envelope_json: dict[str, Any], authenticated_sender: str
    ) -> dict[str, Any]:
        """Take one envelope from the sender the connection authenticated."""
        ...


@dataclass(frozen=True)
class HostSigner:
    """The host's card URL and key: signs the envelopes the host itself originates."""

    card_url: str
    private_key: Ed25519PrivateKey
    kid: str

    def envelope(
        self, coalition_id: str, message_type: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """A host envelope scoped to its recipient (``self``), signed with the host key."""
        envelope: dict[str, Any] = {
            "ext_version": "0.1",
            "coalition_id": coalition_id,
            "event_id": new_ulid(),
            "type": message_type,
            "sender": self.card_url,
            "on_behalf_of": "host",
            "scope": {"audience": "self"},
            "payload": payload,
        }
        envelope["sig"] = sign_envelope(envelope, self.private_key, self.kid)
        return envelope

    def error(
        self, coalition_id: str, code: str, ref: str, message: str | None = None
    ) -> dict[str, Any]:
        detail: dict[str, Any] = {} if message is None else {"message": message}
        return self.envelope(
            coalition_id, "coalition.error", {"code": code, "detail": detail, "ref": ref}
        )


def error_reply(code: str, ref: str, message: str | None = None) -> dict[str, Any]:
    detail: dict[str, Any] = {} if message is None else {"message": message}
    return {"error": {"code": code, "detail": detail, "ref": ref}}


@dataclass
class FakeHost:
    """A host stand-in for tests: checks the sender, validates, and acknowledges with a fake seq."""

    signer: HostSigner
    accepted: list[dict[str, Any]] = field(default_factory=lambda: [])
    calls: list[tuple[dict[str, Any], str]] = field(default_factory=lambda: [])
    _head: dict[str, str] = field(default_factory=lambda: {})

    async def accept(
        self, envelope_json: dict[str, Any], authenticated_sender: str
    ) -> dict[str, Any]:
        self.calls.append((envelope_json, authenticated_sender))
        raw_event = envelope_json.get("event_id")
        ref = raw_event if isinstance(raw_event, str) and is_ulid(raw_event) else new_ulid()
        if envelope_json.get("sender") != authenticated_sender:
            return error_reply("sender_mismatch", ref)
        try:
            validate_envelope(envelope_json)
        except SchemaValidationError as exc:
            return error_reply("schema_invalid", ref, "; ".join(exc.errors)[:500])
        coalition_id = str(envelope_json["coalition_id"])
        seq = 1 + sum(1 for e in self.accepted if e["coalition_id"] == coalition_id)
        previous = self._head.get(
            coalition_id, hashlib.sha256(f"fake-genesis:{coalition_id}".encode()).hexdigest()
        )
        accepted: dict[str, Any] = {
            **envelope_json,
            "seq": seq,
            "ts": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "prev_hash": previous,
        }
        self._head[coalition_id] = prev_hash(accepted)
        self.accepted.append(accepted)
        receipt = self.signer.envelope(
            coalition_id, "coalition.receipt", receipt_payload(coalition_id, accepted)
        )
        return {"accepted": accepted, "receipt": receipt}
