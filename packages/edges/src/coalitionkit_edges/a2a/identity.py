# SPDX-License-Identifier: Apache-2.0
"""Who is on the other end: signed Agent Cards, pinned keys, owner keys and bearer credentials.

A card is untrusted until verified. The verification key is never fetched: it travels inside the
signed card, in the Coalition extension's ``params.keys`` (Ed25519 JWKs with an optional
``not_after``), and a ``jku`` in a signature header is ignored. The first verified key is pinned
per Coalition; from then on a card must verify under the pinned key.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal, cast
from urllib.parse import urlsplit

import httpx
import jwt
from a2a.client import A2ACardResolver
from a2a.extensions.common import find_extension_by_uri
from a2a.types import AgentCard, AgentExtension
from a2a.utils.signing import (
    InvalidSignaturesError,
    NoSignatureError,
    ProtectedHeader,
    create_agent_card_signer,
    create_signature_verifier,
)
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)
from google.protobuf.json_format import MessageToDict

from coalitionkit_contracts import (
    SignatureError,
    jwk_to_public_key,
    public_key_to_jwk,
    verify_envelope,
    verify_owner_proof,
)

from .wire import EXTENSION_URI

Reason = Literal[
    "unsigned",
    "malformed_header",
    "unknown_key",
    "jku_only",
    "expired",
    "revoked",
    "bad_signature",
    "key_changed",
    "unknown_card",
    "bad_join",
]
Clock = Callable[[], datetime]


class CardError(Exception):
    """A card (or the join that carries it) is refused. ``reason`` says why."""

    def __init__(self, reason: Reason, message: str) -> None:
        super().__init__(f"{reason}: {message}")
        self.reason: Reason = reason


class OwnerBindingError(CardError):
    """The owner key in a join payload could not be bound."""


@dataclass(frozen=True)
class CardKey:
    """A card verification key as published in the card."""

    kid: str
    public_key: Ed25519PublicKey
    not_after: datetime | None = None


@dataclass(frozen=True)
class PinnedCard:
    """The key pinned for a card URL at join."""

    card_url: str
    kid: str
    public_key: Ed25519PublicKey


def _utcnow() -> datetime:
    return datetime.now(UTC)


def card_key_entry(
    public_key: Ed25519PublicKey, kid: str, not_after: datetime | None = None
) -> dict[str, str]:
    """One ``params.keys`` entry: an Ed25519 JWK, plus ``not_after`` (RFC 3339) when it expires."""
    entry = public_key_to_jwk(public_key, kid)
    if not_after is not None:
        entry["not_after"] = not_after.astimezone(UTC).isoformat().replace("+00:00", "Z")
    return entry


def coalition_extension(params: Mapping[str, Any], description: str) -> AgentExtension:
    """The Coalition extension entry for ``capabilities.extensions``: declared, never required."""
    return AgentExtension(
        uri=EXTENSION_URI, description=description, required=False, params=dict(params)
    )


def sign_card(
    card: AgentCard,
    private_key: Ed25519PrivateKey,
    kid: str,
    extra_header: Mapping[str, Any] | None = None,
) -> AgentCard:
    """Sign a card with the a2a-sdk signer (EdDSA, typ JOSE, JCS form). Adds one signature."""
    pem = private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    header = cast(
        "ProtectedHeader", {"alg": "EdDSA", "typ": "JOSE", "kid": kid, **(extra_header or {})}
    )
    return create_agent_card_signer(pem, header)(card)


def _parse_not_after(value: object) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise CardError("malformed_header", "not_after must be an RFC 3339 string")
    try:
        parsed = datetime.fromisoformat(value.upper())
    except ValueError as exc:
        raise CardError("malformed_header", "not_after is not an RFC 3339 time") from exc
    if parsed.tzinfo is None:
        raise CardError("malformed_header", "not_after needs an offset")
    return parsed


def card_keys(card: AgentCard) -> dict[str, CardKey]:
    """The verification keys a card publishes, by ``kid``. Entries that are not keys are skipped."""
    extension = find_extension_by_uri(card, EXTENSION_URI)
    if extension is None:
        return {}
    params: dict[str, Any] = MessageToDict(extension.params)
    entries: Any = params.get("keys")
    keys: dict[str, CardKey] = {}
    if not isinstance(entries, list):
        return keys
    for item in cast("list[Any]", entries):
        if not isinstance(item, dict):
            continue
        jwk = cast("dict[str, Any]", item)
        try:
            key = jwk_to_public_key(jwk)
        except SignatureError:
            continue
        kid = str(jwk["kid"])
        keys[kid] = CardKey(kid, key, _parse_not_after(jwk.get("not_after")))
    return keys


def _b64_json(text: str) -> dict[str, Any]:
    try:
        raw = base64.b64decode(text + "=" * (-len(text) % 4), altchars=b"-_", validate=True)
        decoded: Any = json.loads(raw)
    except (binascii.Error, ValueError) as exc:
        raise CardError("malformed_header", "protected header is not base64url JSON") from exc
    if not isinstance(decoded, dict):
        raise CardError("malformed_header", "protected header is not an object")
    return cast("dict[str, Any]", decoded)


def _pem(key: Ed25519PublicKey) -> bytes:
    return key.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)


def _check_signature_key(
    protected: str,
    lookup: Callable[[str], CardKey | None],
    revoked: frozenset[str],
    now: datetime,
) -> CardKey:
    """The key one signature names, once every check except the maths has passed."""
    header = _b64_json(protected)
    kid = header.get("kid")
    if header.get("alg") != "EdDSA" or header.get("typ") != "JOSE" or not isinstance(kid, str):
        raise CardError("malformed_header", "protected header needs alg EdDSA, typ JOSE and kid")
    key = lookup(kid)
    if key is None:
        if "jku" in header:
            raise CardError("jku_only", f"key {kid!r} is only reachable through jku")
        raise CardError("unknown_key", f"no key {kid!r} to verify with")
    if kid in revoked:
        raise CardError("revoked", f"key {kid!r} is revoked")
    if key.not_after is not None and key.not_after <= now:
        raise CardError("expired", f"key {kid!r} expired at {key.not_after.isoformat()}")
    return key


def _usable_keys(
    card: AgentCard,
    lookup: Callable[[str], CardKey | None],
    revoked: frozenset[str],
    now: datetime,
) -> dict[str, CardKey]:
    if not card.signatures:
        raise CardError("unsigned", "the card carries no signature")
    usable: dict[str, CardKey] = {}
    first_problem: CardError | None = None
    for signature in card.signatures:
        try:
            key = _check_signature_key(signature.protected, lookup, revoked, now)
        except CardError as exc:
            first_problem = first_problem or exc
        else:
            usable[key.kid] = key
    if not usable and first_problem is not None:
        raise first_problem
    return usable


def verify_card(
    card: AgentCard,
    lookup: Callable[[str], CardKey | None],
    *,
    revoked: frozenset[str] = frozenset(),
    now: datetime | None = None,
) -> CardKey:
    """Verify a card with the a2a-sdk verifier over the JCS form; return the key that verified.

    ``lookup`` maps a ``kid`` to the key to trust for it: the card's own published keys at join,
    the pinned key afterwards. Raises CardError for an unsigned card, a ``jku``-only, unknown,
    expired or revoked key, or a signature that does not verify (a tampered card).
    """
    usable = _usable_keys(card, lookup, revoked, now or _utcnow())
    used: list[CardKey] = []

    def provider(kid: str | None, jku: str | None) -> bytes:
        # The SDK passes the header's jku along; it is deliberately never looked at.
        key = usable.get(kid or "")
        if key is None:
            raise jwt.InvalidKeyError("key not allowed")
        used.append(key)
        return _pem(key.public_key)

    verifier = create_signature_verifier(provider, ["EdDSA"])
    try:
        verifier(card)
    except NoSignatureError as exc:
        raise CardError("unsigned", "the card carries no signature") from exc
    except InvalidSignaturesError as exc:
        raise CardError("bad_signature", "no signature verifies over the card") from exc
    return used[-1]


class CardRegistry:
    """The cards of one Coalition: verifies them at join, pins the key, binds owner keys."""

    def __init__(self, coalition_id: str, *, clock: Clock = _utcnow) -> None:
        self.coalition_id = coalition_id
        self._clock = clock
        self._lock = threading.Lock()
        self._pins: dict[str, PinnedCard] = {}
        self._owners: dict[str, Ed25519PublicKey] = {}
        self._participants: dict[str, str] = {}
        self._revoked: set[str] = set()

    def revoke(self, kid: str) -> None:
        """Refuse every card signed with this key id from now on."""
        with self._lock:
            self._revoked.add(kid)

    def admit(self, card_url: str, card: AgentCard) -> PinnedCard:
        """Verify a card against the keys it publishes and pin the key that verified.

        A card URL that is already pinned must verify under its pinned key (``key_changed``
        otherwise): a rotation is a new join, not a quiet swap.
        """
        with self._lock:
            revoked = frozenset(self._revoked)
            existing = self._pins.get(card_url)
        now = self._clock()
        if existing is not None:
            return self._verify_pinned(existing, card, revoked, now)
        key = verify_card(card, card_keys(card).get, revoked=revoked, now=now)
        pin = PinnedCard(card_url, key.kid, key.public_key)
        with self._lock:
            return self._pins.setdefault(card_url, pin)

    def verify(self, card_url: str, card: AgentCard) -> PinnedCard:
        """Check a later copy of a card against the key pinned for its URL."""
        with self._lock:
            pin = self._pins.get(card_url)
            revoked = frozenset(self._revoked)
        if pin is None:
            raise CardError("unknown_card", f"{card_url} has not joined")
        return self._verify_pinned(pin, card, revoked, self._clock())

    @staticmethod
    def _verify_pinned(
        pin: PinnedCard, card: AgentCard, revoked: frozenset[str], now: datetime
    ) -> PinnedCard:
        def lookup(kid: str) -> CardKey | None:
            if kid != pin.kid:
                raise CardError("key_changed", f"{pin.card_url} is pinned to key {pin.kid!r}")
            return CardKey(pin.kid, pin.public_key)

        verify_card(card, lookup, revoked=revoked, now=now)
        return pin

    def pinned(self, card_url: str) -> PinnedCard | None:
        with self._lock:
            return self._pins.get(card_url)

    def bind_owner(self, join: Mapping[str, Any]) -> Ed25519PublicKey:
        """Bind the owner key of a ``coalition.join`` envelope to its participant.

        The sender's card must already be pinned and the envelope must verify under the pinned
        agent key. The proof is checked with the contracts' ``verify_owner_proof`` (it must
        verify under the key it carries, name this Coalition, participant and card, and the key
        must differ from the agent key). A card speaks for one participant, and an owner key
        belongs to one participant.
        """
        sender, participant = join.get("sender"), join.get("on_behalf_of")
        payload: Any = join.get("payload")
        if join.get("coalition_id") != self.coalition_id or not isinstance(participant, str):
            raise OwnerBindingError("bad_join", "the join is for another Coalition")
        if not isinstance(sender, str) or not isinstance(payload, dict):
            raise OwnerBindingError("bad_join", "the join has no sender or payload")
        if cast("dict[str, Any]", payload).get("card_url") != sender:
            raise OwnerBindingError("bad_join", "card_url differs from the sender")
        pin = self.pinned(sender)
        if pin is None:
            raise OwnerBindingError("unknown_card", f"{sender} has no verified card")
        try:
            verify_envelope(dict(join), pin.public_key, expected_kid=pin.kid)
            owner_key = verify_owner_proof(join, agent_public_key=pin.public_key)
        except SignatureError as exc:
            raise OwnerBindingError("bad_join", str(exc)) from exc
        raw = owner_key.public_bytes_raw()
        with self._lock:
            speaker = self._participants.get(sender, participant)
            if speaker != participant:
                raise OwnerBindingError("bad_join", f"{sender} already speaks for {speaker!r}")
            for other, key in self._owners.items():
                if other != participant and key.public_bytes_raw() == raw:
                    raise OwnerBindingError(
                        "bad_join", "the owner key belongs to another participant"
                    )
            bound = self._owners.setdefault(participant, owner_key)
            if bound.public_bytes_raw() != raw:
                raise OwnerBindingError(
                    "bad_join", f"{participant!r} already has another owner key"
                )
            self._participants[sender] = participant
        return bound

    def owner_key(self, participant: str) -> Ed25519PublicKey | None:
        with self._lock:
            return self._owners.get(participant)


class CredentialRegistry:
    """Bearer token to card URL. Tokens are kept as SHA-256 digests, never in the clear."""

    def __init__(self) -> None:
        self._by_digest: dict[str, str] = {}

    @staticmethod
    def _digest(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def add(self, token: str, card_url: str) -> None:
        self._by_digest[self._digest(token)] = card_url

    def remove(self, token: str) -> None:
        self._by_digest.pop(self._digest(token), None)

    def authenticate(self, token: str) -> str | None:
        """The card URL this token speaks for, or None."""
        return self._by_digest.get(self._digest(token))


async def fetch_card(
    http: httpx.AsyncClient,
    card_url: str,
    verifier: Callable[[AgentCard], None] | None = None,
) -> AgentCard:
    """Fetch a card with the a2a-sdk resolver, running ``verifier`` on it before returning it."""
    parts = urlsplit(card_url)
    base = f"{parts.scheme}://{parts.netloc}"
    resolver = A2ACardResolver(http, base, parts.path or "/")
    return await resolver.get_agent_card(signature_verifier=verifier)
