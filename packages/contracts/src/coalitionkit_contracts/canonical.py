# SPDX-License-Identifier: Apache-2.0
"""JSON canonicalisation (RFC 8785) and the log hash chain."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

import rfc8785

from .envelope import Envelope


def canonicalize(value: Any) -> bytes:
    """JCS bytes of a JSON value. Integers outside +-(2**53 - 1) are refused by rfc8785."""
    return rfc8785.dumps(value)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def envelope_dict(envelope: Envelope | Mapping[str, Any]) -> dict[str, Any]:
    """An envelope as a plain JSON-ready dict."""
    if isinstance(envelope, Envelope):
        return envelope.to_wire()
    return dict(envelope)


def prev_hash(previous: Envelope | Mapping[str, Any]) -> str:
    """SHA-256 hex of the JCS form of the previous accepted envelope (all fields, ``sig`` too)."""
    return sha256_hex(canonicalize(envelope_dict(previous)))
