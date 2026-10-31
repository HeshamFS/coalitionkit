# SPDX-License-Identifier: Apache-2.0
"""Three-round ECDH PSI, with authenticated encryption against the relay.

The caller pins signing keys to participant identities before construction.
Only the requester exposes a result. Count mode independently shuffles the
returned requester tokens to remove their association with input labels.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import struct
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Literal

from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

from coalitionkit_contracts.canonical import canonicalize
from coalitionkit_contracts.payloads import MatchPayload

from ._group import hash_point, scalar, sodium

LIMIT = 1024
MAX_BLOB = 94000
Reveal = Literal["overlap", "count"]


class PSIError(ValueError):
    """Invalid exchange, authentication, point, or state."""


class DuplicateElement(PSIError):
    """Input contains duplicate elements."""


class CountNotAuthorized(PSIError):
    """The requester is not in the charter's count_trusted list (spec code not_authorized)."""

    code = "not_authorized"


class LimitExceeded(PSIError):
    """Input or encoded blob exceeds the protocol limit."""


@dataclass(frozen=True)
class Context:
    coalition_id: str
    match_id: str
    requester: str
    responder: str
    reveal: Reveal
    #: The task the exchange concerns. Carried in every payload, not in the context digest.
    task_id: str

    def __post_init__(self) -> None:
        if not all(
            (self.coalition_id, self.match_id, self.requester, self.responder, self.task_id)
        ):
            raise PSIError("context identifiers required")
        if self.requester == self.responder or self.reveal not in ("count", "overlap"):
            raise PSIError("invalid context")

    def digest(self) -> bytes:
        return hashlib.sha256(
            canonicalize(
                [
                    "coalition-psi-v1",
                    self.coalition_id,
                    self.match_id,
                    self.requester,
                    self.responder,
                    self.reveal,
                ]
            )
        ).digest()


def _elements(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if len(result) >= LIMIT:
            raise LimitExceeded("too many elements")
        if type(value) is not str or len(value.encode("utf-8")) > 4096:
            raise PSIError("invalid element")
        if value in seen:
            raise DuplicateElement("duplicate element")
        seen.add(value)
        result.append(value)
    return result


def _pack(points: list[bytes]) -> bytes:
    return struct.pack(">H", len(points)) + b"".join(b"\x00\x20" + p for p in points)


def _unpack(data: bytes, offset: int = 0) -> tuple[list[bytes], int]:
    if len(data) < offset + 2:
        raise PSIError("truncated count")
    count = int.from_bytes(data[offset : offset + 2], "big")
    if count > LIMIT:
        raise LimitExceeded("too many points")
    offset += 2
    points: list[bytes] = []
    for _ in range(count):
        if data[offset : offset + 2] != b"\x00\x20" or len(data) < offset + 34:
            raise PSIError("invalid point length")
        point = data[offset + 2 : offset + 34]
        _valid(point)
        points.append(point)
        offset += 34
    if len(set(points)) != count:
        raise DuplicateElement("duplicate point")
    return points, offset


def _valid(point: bytes) -> None:
    if len(point) != 32 or point == bytes(32):
        raise PSIError("invalid point")
    if not sodium.crypto_core_ristretto255_is_valid_point(point):
        raise PSIError("invalid point")


class _Party:
    _own_id = ""
    _peer_id = ""

    def __init__(
        self,
        context: Context,
        values: Iterable[str],
        signing_key: Ed25519PrivateKey,
        peer_key: Ed25519PublicKey,
        *,
        test_scalar: bytes | None = None,
        test_channel_scalar: bytes | None = None,
        test_order: bool = False,
    ) -> None:
        """test_* arguments are TEST ONLY; omit all of them in production."""
        self.context = context
        self._values = _elements(values)
        self._test_order = test_order
        if not test_order:
            secrets.SystemRandom().shuffle(self._values)
        self._sign = signing_key
        self._peer = peer_key
        self._scalar = scalar(test_scalar)
        self._channel = scalar(test_channel_scalar)
        self._public = sodium.crypto_scalarmult_ristretto255_base(self._channel)
        self._state = "new"
        self._setup = b""
        self._request = b""
        self._key = b""

    def _points(self) -> list[bytes]:
        return [
            sodium.crypto_scalarmult_ristretto255(
                self._scalar, hash_point(self.context.digest() + canonicalize(value))
            )
            for value in self._values
        ]

    def _derive(self, peer: bytes) -> bytes:
        _valid(peer)
        shared = sodium.crypto_scalarmult_ristretto255(self._channel, peer)
        return hashlib.sha256(b"coalition-psi-channel-v1" + self.context.digest() + shared).digest()

    def _aad(self, round: str) -> bytes:
        return (
            self.context.digest()
            + round.encode()
            + hashlib.sha256(self._setup + self._request).digest()
        )

    def _seal(self, round: str, body: bytes) -> MatchPayload:
        header = b"CKP1" + bytes([("setup", "request", "response").index(round)])
        raw = header + self.context.digest() + body
        raw += self._sign.sign(raw)
        return MatchPayload.model_validate(
            {
                "match_id": self.context.match_id,
                "task_id": self.context.task_id,
                "peer": self._peer_id,
                "round": round,
                "reveal": self.context.reveal,
                "blob": base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii"),
            }
        )

    def _open(self, payload: MatchPayload, round: str) -> bytes:
        if len(payload.blob) > MAX_BLOB:
            raise LimitExceeded("oversize blob")
        if (payload.match_id, payload.task_id, payload.peer, payload.reveal, payload.round) != (
            self.context.match_id,
            self.context.task_id,
            self._own_id,
            self.context.reveal,
            round,
        ):
            raise PSIError("wrong exchange")
        try:
            raw = base64.b64decode(
                payload.blob + "=" * (-len(payload.blob) % 4), altchars=b"-_", validate=True
            )
            if base64.urlsafe_b64encode(raw).rstrip(b"=").decode() != payload.blob:
                raise PSIError("noncanonical base64url")
            self._peer.verify(raw[-64:], raw[:-64])
        except (ValueError, InvalidSignature) as exc:
            raise PSIError("invalid signed blob") from exc
        expected = b"CKP1" + bytes([("setup", "request", "response").index(round)])
        if raw[:37] != expected + self.context.digest():
            raise PSIError("wrong context or round")
        return raw[37:-64]

    def _decrypt(self, body: bytes, round: str) -> bytes:
        try:
            return ChaCha20Poly1305(self._key).decrypt(bytes(12), body, self._aad(round))
        except (InvalidTag, ValueError) as exc:
            raise PSIError("invalid encrypted blob") from exc

    def _encrypt(self, body: bytes, round: str) -> bytes:
        # Distinct directional keys: one message per key, with a fixed nonce.
        return ChaCha20Poly1305(self._key).encrypt(bytes(12), body, self._aad(round))

    def _advance_key(self) -> None:
        self._key = hashlib.sha256(b"response" + self._key).digest()

    def _require(self, state: str) -> None:
        if self._state != state:
            raise PSIError("invalid exchange state")


class Responder(_Party):
    def __init__(
        self,
        context: Context,
        values: Iterable[str],
        signing_key: Ed25519PrivateKey,
        peer_key: Ed25519PublicKey,
        *,
        count_trusted: Iterable[str] = (),
        test_scalar: bytes | None = None,
        test_channel_scalar: bytes | None = None,
        test_order: bool = False,
    ) -> None:
        """count_trusted is the charter's list for this Coalition; count needs membership."""
        if context.reveal == "count" and context.requester not in set(count_trusted):
            raise CountNotAuthorized("requester is not in count_trusted")
        super().__init__(
            context,
            values,
            signing_key,
            peer_key,
            test_scalar=test_scalar,
            test_channel_scalar=test_channel_scalar,
            test_order=test_order,
        )
        self._own_id = context.responder
        self._peer_id = context.requester

    def setup(self) -> MatchPayload:
        self._require("new")
        message = self._seal("setup", self._public)
        self._setup = message.blob.encode()
        self._state = "setup"
        return message

    def respond(self, request: MatchPayload) -> MatchPayload:
        self._require("setup")
        body = self._open(request, "request")
        if len(body) < 32:
            raise PSIError("truncated request")
        self._key = self._derive(body[:32])
        plain = self._decrypt(body[32:], "request")
        points, end = _unpack(plain)
        if end != len(plain):
            raise PSIError("trailing bytes")
        doubled = [sodium.crypto_scalarmult_ristretto255(self._scalar, p) for p in points]
        if self.context.reveal == "count":
            if self._test_order:
                doubled.reverse()
            else:
                secrets.SystemRandom().shuffle(doubled)
        self._request = request.blob.encode()
        self._advance_key()
        message = self._seal(
            "response", self._encrypt(_pack(doubled) + _pack(self._points()), "response")
        )
        self._state = "done"
        return message


class Requester(_Party):
    def __init__(
        self,
        context: Context,
        values: Iterable[str],
        signing_key: Ed25519PrivateKey,
        peer_key: Ed25519PublicKey,
        *,
        on_result: Callable[[list[str] | int], None] | None = None,
        **test_only: bytes | bool | None,
    ) -> None:
        super().__init__(context, values, signing_key, peer_key, **test_only)  # type: ignore[arg-type]
        self._own_id = context.requester
        self._peer_id = context.responder
        self._on_result = on_result

    def request(self, setup: MatchPayload) -> MatchPayload:
        self._require("new")
        peer = self._open(setup, "setup")
        self._key = self._derive(peer)
        self._setup = setup.blob.encode()
        message = self._seal(
            "request", self._public + self._encrypt(_pack(self._points()), "request")
        )
        self._request = message.blob.encode()
        self._advance_key()
        self._state = "request"
        return message

    def finish(self, response: MatchPayload) -> list[str] | int:
        self._require("request")
        plain = self._decrypt(self._open(response, "response"), "response")
        doubled, end = _unpack(plain)
        other, end = _unpack(plain, end)
        if end != len(plain) or len(doubled) != len(self._values):
            raise PSIError("invalid response lengths")
        tokens = {sodium.crypto_scalarmult_ristretto255(self._scalar, p) for p in other}
        if self.context.reveal == "count":
            self._state = "done"
            count = len(tokens.intersection(doubled))
            if self._on_result is not None:
                self._on_result(count)
            return count
        overlap = sorted(
            value for value, point in zip(self._values, doubled, strict=True) if point in tokens
        )
        self._state = "done"
        if self._on_result is not None:
            self._on_result(overlap.copy())
        return overlap
