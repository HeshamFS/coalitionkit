# SPDX-License-Identifier: Apache-2.0
"""Typed boundary to PySodium's libsodium ristretto255 operations.

All group arithmetic stays in libsodium. SHA-512 XMD follows RFC 9380 section
5.4.1; ristretto255 mapping follows section 8.5 with a protocol-specific DST.
"""

import hashlib
from importlib import import_module
from typing import Protocol, cast


class Sodium(Protocol):
    def crypto_core_ristretto255_from_hash(self, value: bytes) -> bytes: ...
    def crypto_core_ristretto255_is_valid_point(self, value: bytes) -> bool: ...
    def crypto_core_ristretto255_scalar_random(self) -> bytes: ...
    def crypto_core_ristretto255_scalar_invert(self, value: bytes) -> bytes: ...
    def crypto_scalarmult_ristretto255(self, scalar: bytes, point: bytes) -> bytes: ...
    def crypto_scalarmult_ristretto255_base(self, scalar: bytes) -> bytes: ...


class _LazySodium:
    def __getattr__(self, name: str) -> object:
        try:
            module = import_module("pysodium")
        except (ImportError, OSError, ValueError, TypeError) as exc:
            raise RuntimeError(
                "Private set intersection requires coalitionkit[psi] and libsodium >=1.0.18"
            ) from exc
        return getattr(module, name)


sodium = cast(Sodium, _LazySodium())
DST = b"CoalitionKit-v0.1-PSI-ristretto255_XMD:SHA-512_R255MAP_RO_"


def hash_point(message: bytes) -> bytes:
    dst = DST + bytes([len(DST)])
    b0 = hashlib.sha512(bytes(128) + message + b"\x00\x40\x00" + dst).digest()
    uniform = hashlib.sha512(b0 + b"\x01" + dst).digest()
    return sodium.crypto_core_ristretto255_from_hash(uniform)


def scalar(value: bytes | None = None) -> bytes:
    if value is None:
        return sodium.crypto_core_ristretto255_scalar_random()
    order = 2**252 + 27742317777372353535851937790883648493
    if len(value) != 32 or not 0 < int.from_bytes(value, "little") < order:
        raise ValueError("invalid scalar")
    return value
