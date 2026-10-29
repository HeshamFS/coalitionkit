# SPDX-License-Identifier: Apache-2.0
"""Authenticated idempotency: how a host treats an ``event_id`` it may already hold."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from .canonical import canonicalize, envelope_dict, sha256_hex
from .envelope import HOST_FIELDS, Envelope

Outcome = Literal["new", "replay", "mismatch"]


@dataclass(frozen=True)
class StoredSubmission:
    """What the host keeps per accepted event: who sent it and the digest of what they sent."""

    sender: str
    digest: str


def idempotency_key(envelope: Envelope | Mapping[str, Any]) -> tuple[str, str]:
    """The lookup key: ``(coalition_id, event_id)``."""
    data = envelope_dict(envelope)
    return str(data.get("coalition_id")), str(data.get("event_id"))


def submission_digest(envelope: Envelope | Mapping[str, Any]) -> str:
    """SHA-256 hex of the JCS form of the envelope without the host fields (``sig`` included)."""
    data = {k: v for k, v in envelope_dict(envelope).items() if k not in HOST_FIELDS}
    return sha256_hex(canonicalize(data))


def classify_submission(
    original: StoredSubmission | None,
    authenticated_sender: str,
    envelope: Envelope | Mapping[str, Any],
) -> Outcome:
    """``new`` (nothing stored), ``replay`` (return the original acknowledgement) or ``mismatch``.

    ``mismatch`` is answered with ``duplicate_mismatch`` and discloses nothing about the original:
    the same answer for a different sender and for a different envelope.
    """
    if original is None:
        return "new"
    same_sender = original.sender == authenticated_sender
    same_bytes = original.digest == submission_digest(envelope)
    return "replay" if same_sender and same_bytes else "mismatch"
