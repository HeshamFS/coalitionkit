# SPDX-License-Identifier: Apache-2.0
"""Card identity: signed cards, pinned keys, jku, expiry, revocation and owner binding."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import pytest
from a2a.types import AgentCard
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from examples import COALITION_ID, make_envelope
from google.protobuf.json_format import MessageToDict, ParseDict

from coalitionkit_contracts import new_ulid, sign_envelope, sign_owner_proof
from coalitionkit_edges.a2a import CardError, CardRegistry, OwnerBindingError

if TYPE_CHECKING:
    from conftest import MakeCard, Member

URL = "https://agents.example.org/p2/card.json"


def join_envelope(member: Member, **overrides: Any) -> dict[str, Any]:
    jwk = member.owner_jwk()
    payload = {
        "card_url": URL,
        "owner_key": jwk,
        "owner_proof": sign_owner_proof(COALITION_ID, "p2", URL, jwk, member.owner_key),
        "roles_requested": ["member"],
        "surfaces": ["web"],
        "vault": "local",
    }
    envelope = make_envelope("coalition.join", sender=URL, payload=payload, **overrides)
    envelope["sig"] = sign_envelope(envelope, member.key, member.kid)
    return envelope


def test_signed_card_is_admitted_and_its_key_pinned(member: Member, make_card: MakeCard) -> None:
    registry = CardRegistry(COALITION_ID)
    pin = registry.admit(URL, make_card())
    assert pin.kid == member.kid
    assert pin.public_key.public_bytes_raw() == member.key.public_key().public_bytes_raw()
    assert registry.pinned(URL) == pin


def test_unsigned_card_is_rejected(make_card: MakeCard) -> None:
    with pytest.raises(CardError) as exc:
        CardRegistry(COALITION_ID).admit(URL, make_card(sign=False))
    assert exc.value.reason == "unsigned"


def test_tampered_card_fails_verification(make_card: MakeCard) -> None:
    card = make_card()
    card.description = "A member of other Coalitions"
    with pytest.raises(CardError) as exc:
        CardRegistry(COALITION_ID).admit(URL, card)
    assert exc.value.reason == "bad_signature"


def test_key_only_reachable_through_jku_is_rejected(make_card: MakeCard) -> None:
    card = make_card(publish_key=False, extra_header={"jku": "https://keys.example.org/jwks.json"})
    with pytest.raises(CardError) as exc:
        CardRegistry(COALITION_ID).admit(URL, card)
    assert exc.value.reason == "jku_only"


def test_card_without_published_key_or_jku_is_rejected(make_card: MakeCard) -> None:
    with pytest.raises(CardError) as exc:
        CardRegistry(COALITION_ID).admit(URL, make_card(publish_key=False))
    assert exc.value.reason == "unknown_key"


def test_expired_key_is_rejected(make_card: MakeCard) -> None:
    card = make_card(not_after=datetime.now(UTC) - timedelta(minutes=1))
    with pytest.raises(CardError) as exc:
        CardRegistry(COALITION_ID).admit(URL, card)
    assert exc.value.reason == "expired"


def test_key_is_valid_until_its_not_after(make_card: MakeCard) -> None:
    deadline = datetime(2030, 1, 1, tzinfo=UTC)
    card = make_card(not_after=deadline)
    CardRegistry(COALITION_ID, clock=lambda: deadline - timedelta(seconds=1)).admit(URL, card)
    with pytest.raises(CardError) as exc:
        CardRegistry(COALITION_ID, clock=lambda: deadline).admit(URL, card)
    assert exc.value.reason == "expired"


def test_revoked_key_is_rejected_before_and_after_pinning(
    member: Member, make_card: MakeCard
) -> None:
    registry = CardRegistry(COALITION_ID)
    registry.revoke(member.kid)
    with pytest.raises(CardError) as exc:
        registry.admit(URL, make_card())
    assert exc.value.reason == "revoked"
    later = CardRegistry(COALITION_ID)
    later.admit(URL, make_card())
    later.revoke(member.kid)
    with pytest.raises(CardError) as again:
        later.verify(URL, make_card())
    assert again.value.reason == "revoked"


def test_pinned_key_cannot_be_swapped_by_a_new_card(member: Member, make_card: MakeCard) -> None:
    registry = CardRegistry(COALITION_ID)
    registry.admit(URL, make_card())
    member.key = Ed25519PrivateKey.generate()  # a self-consistent card under another key
    with pytest.raises(CardError) as exc:
        registry.admit(URL, make_card(kid="other-key"))
    assert exc.value.reason == "key_changed"


def test_owner_key_is_bound_from_the_join(member: Member, make_card: MakeCard) -> None:
    registry = CardRegistry(COALITION_ID)
    registry.admit(URL, make_card())
    bound = registry.bind_owner(join_envelope(member))
    assert bound.public_bytes_raw() == member.owner_key.public_key().public_bytes_raw()
    assert registry.owner_key("p2") == bound


def test_owner_key_equal_to_the_agent_key_is_refused(member: Member, make_card: MakeCard) -> None:
    registry = CardRegistry(COALITION_ID)
    registry.admit(URL, make_card())
    member.owner_key, member.owner_kid = member.key, member.kid
    with pytest.raises(OwnerBindingError):
        registry.bind_owner(join_envelope(member))


def test_join_with_a_forged_owner_proof_is_refused(member: Member, make_card: MakeCard) -> None:
    registry = CardRegistry(COALITION_ID)
    registry.admit(URL, make_card())
    join = join_envelope(member)
    join["payload"]["owner_proof"] = sign_owner_proof(
        COALITION_ID, "p2", URL, member.owner_jwk(), Ed25519PrivateKey.generate()
    )
    with pytest.raises(OwnerBindingError):
        registry.bind_owner(join)


def test_join_from_a_card_never_admitted_is_refused(member: Member) -> None:
    with pytest.raises(OwnerBindingError) as exc:
        CardRegistry(COALITION_ID).bind_owner(join_envelope(member))
    assert exc.value.reason == "unknown_card"


def test_join_for_another_coalition_is_refused(member: Member, make_card: MakeCard) -> None:
    registry = CardRegistry(new_ulid())
    registry.admit(URL, make_card())
    with pytest.raises(OwnerBindingError):
        registry.bind_owner(join_envelope(member))


def test_a_participant_keeps_its_first_owner_key(member: Member, make_card: MakeCard) -> None:
    registry = CardRegistry(COALITION_ID)
    registry.admit(URL, make_card())
    registry.bind_owner(join_envelope(member))
    member.owner_key = Ed25519PrivateKey.generate()
    with pytest.raises(OwnerBindingError):
        registry.bind_owner(join_envelope(member, event_id=new_ulid()))


def test_card_still_verifies_after_a_json_round_trip(make_card: MakeCard) -> None:
    again = ParseDict(MessageToDict(make_card()), AgentCard())
    CardRegistry(COALITION_ID).admit(URL, again)
