# SPDX-License-Identifier: Apache-2.0
"""consent_sig is the owner's: it fails with the agent key and passes with the owner key."""

from __future__ import annotations

import copy
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from examples import COALITION_ID, PAYLOADS, PLAN_ID, load_vector, make_envelope

from coalitionkit_contracts import (
    OwnerKeyConflictError,
    SignatureError,
    check_owner_key_unique,
    consent_payload,
    jwk_thumbprint,
    jwk_to_public_key,
    public_key_to_jwk,
    sha256_hex,
    sign_consent,
    sign_envelope,
    sign_owner_proof,
    validate_envelope,
    verify_consent,
    verify_decision,
    verify_envelope,
    verify_owner_proof,
)

AGENT = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
OWNER = Ed25519PrivateKey.from_private_bytes(bytes(range(1, 33)))
PART = "p2"
OWNER_JWK = public_key_to_jwk(OWNER.public_key(), "owner-1")


def decision(**changes: Any) -> dict[str, Any]:
    payload = {k: v for k, v in PAYLOADS["coalition.decide"].items() if k != "consent_sig"}
    payload.update(changes)
    payload["consent_sig"] = sign_consent(COALITION_ID, payload, OWNER, "owner-1", participant=PART)
    return payload


def decide_envelope(payload: dict[str, Any]) -> dict[str, Any]:
    env = make_envelope("coalition.decide", payload=payload)
    env["sig"] = sign_envelope(env, AGENT, "agent-1")
    return env


def consent_ok(coalition_id: str, payload: dict[str, Any]) -> bool:
    try:
        verify_consent(coalition_id, payload, OWNER.public_key(), participant=PART)
    except SignatureError:
        return False
    return True


def test_owner_key_verifies_and_agent_key_does_not() -> None:
    payload = decision()
    assert verify_consent(
        COALITION_ID, payload, OWNER.public_key(), participant=PART, expected_kid="owner-1"
    )
    with pytest.raises(SignatureError):
        verify_consent(COALITION_ID, payload, AGENT.public_key(), participant=PART)


def test_agent_signed_consent_sig_is_rejected_as_owner_consent() -> None:
    payload = decision()
    payload["consent_sig"] = sign_consent(COALITION_ID, payload, AGENT, "agent-1", participant=PART)
    with pytest.raises(SignatureError):
        verify_consent(COALITION_ID, payload, OWNER.public_key(), participant=PART)


@pytest.mark.parametrize(
    "change",
    [
        {"consent": False},
        {"choice": "other"},
        {"decided_at": "2026-10-29T10:16:00Z"},
        {"subject": {"kind": "plan", "id": PLAN_ID, "revision": 2}},
        {"subject": {"kind": "task", "id": PLAN_ID, "revision": 1}},
    ],
)
def test_any_signed_field_change_breaks_consent(change: dict[str, Any]) -> None:
    assert not consent_ok(COALITION_ID, {**decision(), **change})


def test_consent_binds_the_coalition() -> None:
    assert not consent_ok("01M4XRC000000G40R40M30E20A", decision())


def test_consent_binds_the_participant() -> None:
    payload = decision()  # signed for p2
    assert consent_ok(COALITION_ID, payload)
    with pytest.raises(SignatureError):
        verify_consent(COALITION_ID, payload, OWNER.public_key(), participant="p5")
    # replayed inside an envelope that speaks for p5 (even correctly agent-signed)
    env = make_envelope("coalition.decide", payload=payload)
    env["on_behalf_of"] = "p5"
    env["sig"] = sign_envelope(env, AGENT, "agent-1")
    with pytest.raises(SignatureError):
        verify_decision(env, AGENT.public_key(), OWNER.public_key())
    # an envelope with no on_behalf_of fails closed
    env2 = decide_envelope(payload)
    env2["on_behalf_of"] = ""
    with pytest.raises(SignatureError):
        verify_decision(env2, AGENT.public_key(), OWNER.public_key())


def test_jwk_thumbprint_rfc7638() -> None:
    jwk = {"kty": "OKP", "crv": "Ed25519", "x": "11qYAYKxCrfVS_7TyWQHOg7hcvPapiMlrwIaaPcHURo"}
    assert jwk_thumbprint({**jwk, "kid": "x"}) == "kPrK_qmxVWaYVA9wwBF6Iuo3vVzz7TxHCTwXBygrS4k"
    assert jwk_thumbprint(OWNER_JWK) == jwk_thumbprint({**OWNER_JWK, "kid": "renamed"})


def test_owner_key_unique_per_coalition() -> None:
    t = jwk_thumbprint(OWNER_JWK)
    check_owner_key_unique({}, "p2", t)
    check_owner_key_unique({"p2": t}, "p2", t)  # same participant re-joining
    check_owner_key_unique({"p5": "other"}, "p2", t)
    with pytest.raises(OwnerKeyConflictError):
        check_owner_key_unique({"p5": t}, "p2", t)


def test_missing_or_malformed_consent_sig_fails() -> None:
    payload = decision()
    assert not consent_ok(COALITION_ID, {k: v for k, v in payload.items() if k != "consent_sig"})
    assert not consent_ok(COALITION_ID, {**payload, "consent_sig": "abc"})
    assert not consent_ok(COALITION_ID, {k: v for k, v in payload.items() if k != "decided_at"})


def test_a_decision_counts_only_with_both_signatures() -> None:
    env = decide_envelope(decision())
    validate_envelope(env)
    verify_decision(env, AGENT.public_key(), OWNER.public_key())
    # the agent signed both the envelope and the consent: the agent alone does not count
    forged = decision()
    forged["consent_sig"] = sign_consent(COALITION_ID, forged, AGENT, "agent-1", participant=PART)
    with pytest.raises(SignatureError):
        verify_decision(decide_envelope(forged), AGENT.public_key(), OWNER.public_key())
    # a consent signed by some other key
    other = Ed25519PrivateKey.from_private_bytes(bytes(range(7, 39)))
    wrong = decision()
    wrong["consent_sig"] = sign_consent(COALITION_ID, wrong, other, "owner-1", participant=PART)
    with pytest.raises(SignatureError):
        verify_decision(decide_envelope(wrong), AGENT.public_key(), OWNER.public_key())
    # a valid consent under an envelope the agent did not sign
    with pytest.raises(SignatureError):
        verify_decision(decide_envelope(decision()), OWNER.public_key(), OWNER.public_key())


def test_verify_decision_needs_a_decide_envelope() -> None:
    with pytest.raises(SignatureError):
        verify_decision(make_envelope("coalition.offer"), AGENT.public_key(), OWNER.public_key())


def join_envelope(owner_jwk: dict[str, str] | None = None) -> dict[str, Any]:
    jwk = owner_jwk or OWNER_JWK
    env = make_envelope("coalition.join")
    card_url = env["payload"]["card_url"]
    proof = sign_owner_proof(COALITION_ID, env["on_behalf_of"], card_url, jwk, OWNER)
    env["payload"] = {**env["payload"], "owner_key": jwk, "owner_proof": proof}
    env["sig"] = sign_envelope(env, AGENT, "agent-1")
    return env


def test_owner_proof_binds_the_key_to_the_participant() -> None:
    env = join_envelope()
    validate_envelope(env)
    pinned = verify_owner_proof(env, agent_public_key=AGENT.public_key())
    assert pinned.public_bytes_raw() == OWNER.public_key().public_bytes_raw()


def test_owner_proof_rejects_other_participant_card_or_key() -> None:
    env = join_envelope()
    with pytest.raises(SignatureError):
        verify_owner_proof({**env, "on_behalf_of": "p9"})
    moved = copy.deepcopy(env)
    moved["payload"]["card_url"] = "https://agents.example.org/other/card.json"
    with pytest.raises(SignatureError):
        verify_owner_proof(moved)
    # the proof was made by OWNER but the join claims the agent's key as the owner key
    swapped = join_envelope()
    swapped["payload"]["owner_key"] = public_key_to_jwk(AGENT.public_key(), "owner-1")
    with pytest.raises(SignatureError):
        verify_owner_proof(swapped)


def test_owner_key_must_differ_from_the_agent_key() -> None:
    jwk = public_key_to_jwk(AGENT.public_key(), "agent-1")
    env = make_envelope("coalition.join")
    proof = sign_owner_proof(
        COALITION_ID, env["on_behalf_of"], env["payload"]["card_url"], jwk, AGENT
    )
    env["payload"] = {**env["payload"], "owner_key": jwk, "owner_proof": proof}
    assert verify_owner_proof(env)
    with pytest.raises(SignatureError):
        verify_owner_proof(env, agent_public_key=AGENT.public_key())


def test_jwk_round_trip_and_bad_jwk() -> None:
    key = jwk_to_public_key(OWNER_JWK)
    assert key.public_bytes_raw() == OWNER.public_key().public_bytes_raw()
    for bad in ({**OWNER_JWK, "crv": "X25519"}, {**OWNER_JWK, "x": "AA"}, {"kty": "OKP"}):
        with pytest.raises(SignatureError):
            jwk_to_public_key(bad)


CONSENT = load_vector("consent.json")


def vector_key(name: str) -> Ed25519PublicKey:
    return Ed25519PublicKey.from_public_bytes(bytes.fromhex(CONSENT[name]["public_key_hex"]))


def test_consent_vector() -> None:
    agent, owner = vector_key("agent_key"), vector_key("owner_key")
    env = CONSENT["decide_envelope"]
    payload = consent_payload(env["coalition_id"], env["payload"], participant=env["on_behalf_of"])
    assert payload.decode() == CONSENT["consent_payload_utf8"]
    assert sha256_hex(payload) == CONSENT["consent_payload_sha256"]
    verify_decision(env, agent, owner)
    assert verify_envelope(env, agent) == CONSENT["agent_key"]["kid"]
    with pytest.raises(SignatureError):
        verify_consent(env["coalition_id"], env["payload"], agent, participant=env["on_behalf_of"])
    with pytest.raises(SignatureError):
        verify_envelope(env, owner)
    pinned = verify_owner_proof(CONSENT["join_envelope"], agent_public_key=agent)
    assert pinned.public_bytes_raw() == owner.public_bytes_raw()
    validate_envelope(env)
    validate_envelope(CONSENT["join_envelope"])


def _variant(x: str, kind: str) -> str:
    if kind == "padded":
        return x + "="
    if kind == "standard-alphabet":
        return x.replace("-", "+").replace("_", "/")
    # flip the unused low bit of the final character: same 32 bytes, non-canonical text
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    return x[:-1] + alphabet[alphabet.index(x[-1]) ^ 1]


@pytest.mark.parametrize("kind", ["padded", "standard-alphabet", "trailing-bits"])
def test_non_canonical_owner_key_encodings_are_rejected(kind: str) -> None:
    jwk = dict(OWNER_JWK)
    jwk["x"] = _variant(OWNER_JWK["x"], kind)
    if jwk["x"] == OWNER_JWK["x"]:
        pytest.skip("variant is identical for this key")
    with pytest.raises(SignatureError):
        jwk_to_public_key(jwk)
