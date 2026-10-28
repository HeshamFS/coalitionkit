# SPDX-License-Identifier: Apache-2.0
"""The shared vectors in spec/vectors must pass."""

from __future__ import annotations

import base64
import json
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from examples import load_vector

from coalitionkit_contracts import (
    SignatureError,
    canonicalize,
    prev_hash,
    sha256_hex,
    sign_envelope,
    signing_payload,
    validate_envelope,
    verify_envelope,
)

JCS = load_vector("jcs.json")
SIGNING = load_vector("signing.json")


@pytest.mark.parametrize("case", JCS["cases"], ids=[c["name"] for c in JCS["cases"]])
def test_jcs_case(case: dict[str, Any]) -> None:
    data = canonicalize(json.loads(case["input_json"]))
    assert data.decode("utf-8") == case["canonical_utf8"]
    assert data.hex() == case["canonical_hex"]
    assert sha256_hex(data) == case["sha256"]


@pytest.mark.parametrize("case", JCS["error_cases"], ids=[c["name"] for c in JCS["error_cases"]])
def test_jcs_error_case(case: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        canonicalize(json.loads(case["input_json"]))


def test_signing_vector_is_reproduced() -> None:
    key_info = SIGNING["test_key"]
    key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(key_info["private_seed_hex"]))
    public = Ed25519PublicKey.from_public_bytes(bytes.fromhex(key_info["public_key_hex"]))
    assert key.public_key().public_bytes_raw() == public.public_bytes_raw()
    jwk_x = key_info["public_jwk"]["x"]
    assert base64.urlsafe_b64decode(jwk_x + "=") == public.public_bytes_raw()

    unsigned = SIGNING["envelope_without_sig"]
    assert signing_payload(unsigned).decode("utf-8") == SIGNING["signing_payload_utf8"]
    assert sha256_hex(signing_payload(unsigned)) == SIGNING["signing_payload_sha256"]
    assert sign_envelope(unsigned, key, key_info["kid"]) == SIGNING["jws"]


def test_signing_vector_verifies_and_chains() -> None:
    public = Ed25519PublicKey.from_public_bytes(
        bytes.fromhex(SIGNING["test_key"]["public_key_hex"])
    )
    assert verify_envelope(SIGNING["envelope_signed"], public) == "test-key-1"
    # The host fields are outside the signature.
    assert verify_envelope(SIGNING["envelope_accepted_by_host"], public) == "test-key-1"
    assert prev_hash(SIGNING["envelope_accepted_by_host"]) == SIGNING["prev_hash_of_accepted"]
    validate_envelope(SIGNING["envelope_accepted_by_host"])
    with pytest.raises(SignatureError):
        verify_envelope(SIGNING["envelope_signed"], public, expected_kid="other")
