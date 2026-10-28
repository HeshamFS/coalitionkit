# SPDX-License-Identifier: Apache-2.0
"""Deterministic ULID-shaped identifiers derived from content."""

from __future__ import annotations

import hashlib

_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def derive_ulid(*parts: str) -> str:
    """A valid 26-character ULID computed from ``parts``; the same parts give the same ID."""
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).digest()
    value = int.from_bytes(digest[:16], "big")  # 128 bits: the first character is at most 7
    chars: list[str] = []
    for _ in range(26):
        chars.append(_ALPHABET[value & 31])
        value >>= 5
    return "".join(reversed(chars))
