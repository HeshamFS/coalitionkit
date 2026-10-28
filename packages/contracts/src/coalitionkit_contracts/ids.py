# SPDX-License-Identifier: Apache-2.0
"""ULIDs: 48-bit millisecond timestamp plus 80 random bits, as 26 Crockford base32 characters."""

from __future__ import annotations

import re
import secrets
import time

from ._types import ULID_PATTERN

_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_ULID_RE = re.compile(ULID_PATTERN)
_MAX_TIME_MS = 2**48 - 1


def _encode(value: int, length: int) -> str:
    chars: list[str] = []
    for _ in range(length):
        chars.append(_ALPHABET[value & 31])
        value >>= 5
    return "".join(reversed(chars))


def new_ulid(*, now_ms: int | None = None, entropy: bytes | None = None) -> str:
    """Create a ULID. ``now_ms`` and ``entropy`` (10 bytes) exist for tests."""
    millis = time.time_ns() // 1_000_000 if now_ms is None else now_ms
    if not 0 <= millis <= _MAX_TIME_MS:
        raise ValueError("timestamp out of the 48-bit range")
    raw = secrets.token_bytes(10) if entropy is None else entropy
    if len(raw) != 10:
        raise ValueError("entropy must be exactly 10 bytes")
    return _encode(millis, 10) + _encode(int.from_bytes(raw, "big"), 16)


def is_ulid(value: object) -> bool:
    """True when ``value`` matches the ULID pattern used by the JSON Schemas."""
    return isinstance(value, str) and _ULID_RE.fullmatch(value) is not None


def ulid_timestamp_ms(value: str) -> int:
    """The millisecond timestamp encoded in a ULID."""
    if not is_ulid(value):
        raise ValueError("not a ULID")
    number = 0
    for char in value[:10]:
        number = (number << 5) | _ALPHABET.index(char)
    return number
