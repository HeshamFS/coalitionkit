# SPDX-License-Identifier: Apache-2.0
"""Signatures break on any change; prev_hash changes when any field changes."""

from __future__ import annotations

import base64
import copy
import json
from collections.abc import Iterator
from typing import Any, cast

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from examples import make_envelope

from coalitionkit_contracts import (
    HOST_FIELDS,
    Envelope,
    SignatureError,
    is_valid_signature,
    prev_hash,
    sign_envelope,
    verify_envelope,
)

KEY = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
OTHER = Ed25519PrivateKey.from_private_bytes(bytes(range(1, 33)))
KID = "k1"


def leaves(value: Any, path: tuple[Any, ...] = ()) -> Iterator[tuple[Any, ...]]:
    if isinstance(value, dict):
        for key, child in cast("dict[str, Any]", value).items():
            yield from leaves(child, (*path, key))
    elif isinstance(value, list):
        for index, child in enumerate(cast("list[Any]", value)):
            yield from leaves(child, (*path, index))
    else:
        yield path


def get(value: Any, path: tuple[Any, ...]) -> Any:
    for step in path:
        value = value[step]
    return value


def change(leaf: Any) -> Any:
    if isinstance(leaf, bool):
        return not leaf
    if isinstance(leaf, int):
        return leaf + 1
    if isinstance(leaf, float):
        return leaf + 1.0
    return f"{leaf}x"


def mutated(data: dict[str, Any], path: tuple[Any, ...]) -> dict[str, Any]:
    out = copy.deepcopy(data)
    parent = get(out, path[:-1])
    parent[path[-1]] = change(parent[path[-1]])
    return out


def signed() -> dict[str, Any]:
    data = make_envelope()
    data["sig"] = sign_envelope(data, KEY, KID)
    return data


def test_round_trip_and_kid() -> None:
    data = signed()
    assert verify_envelope(data, KEY.public_key()) == KID
    assert verify_envelope(Envelope.model_validate(data), KEY.public_key()) == KID
    assert is_valid_signature(data, KEY.public_key(), expected_kid=KID)
    assert not is_valid_signature(data, KEY.public_key(), expected_kid="k2")


def test_header_is_eddsa_jose_with_kid() -> None:
    header = signed()["sig"].split(".")[0]
    decoded = json.loads(base64.urlsafe_b64decode(header + "=" * (-len(header) % 4)))
    assert decoded == {"alg": "EdDSA", "typ": "JOSE", "kid": KID}


def test_wrong_key_fails() -> None:
    assert not is_valid_signature(signed(), OTHER.public_key())


def test_any_one_signed_field_change_breaks_verification() -> None:
    data = signed()
    paths = [p for p in leaves(data) if p[0] not in ("sig", *HOST_FIELDS)]
    assert len(paths) > 15
    for path in paths:
        assert not is_valid_signature(mutated(data, path), KEY.public_key()), path


def test_removing_or_adding_a_signed_field_breaks_verification() -> None:
    data = signed()
    for field in ("causation_id", "correlation_id", "on_behalf_of"):
        cut = {k: v for k, v in data.items() if k != field}
        assert not is_valid_signature(cut, KEY.public_key())
    assert not is_valid_signature({**data, "extra": 1}, KEY.public_key())


def test_host_fields_are_not_signed() -> None:
    data = signed()
    accepted = {**data, "seq": 9, "ts": "2026-10-29T09:30:00Z", "prev_hash": "0" * 64}
    assert is_valid_signature(accepted, KEY.public_key())
    assert is_valid_signature({**data, "seq": 10}, KEY.public_key())


@pytest.mark.parametrize(
    "sig",
    [
        "",
        "abc",
        "a.b",
        "a.b.c.d",
        "eyJhbGciOiJFZERTQSIsImtpZCI6ImsxIiwidHlwIjoiSk9TRSJ9.cGF5bG9hZA.AAAA",  # attached payload
        "!!!..!!!",
        "e30..AAAA",  # empty header object
    ],
)
def test_malformed_signatures_fail(sig: str) -> None:
    assert not is_valid_signature({**signed(), "sig": sig}, KEY.public_key())


def test_missing_sig_fails() -> None:
    data = signed()
    del data["sig"]
    with pytest.raises(SignatureError):
        verify_envelope(data, KEY.public_key())


def test_header_variants_fail() -> None:
    data = make_envelope()
    sig_part = sign_envelope(data, KEY, KID).split("..")[1]
    for header in (
        {"alg": "none", "typ": "JOSE", "kid": KID},
        {"alg": "EdDSA", "typ": "JWT", "kid": KID},
        {"alg": "EdDSA", "typ": "JOSE"},
        {"alg": "EdDSA", "typ": "JOSE", "kid": 1},
        {"alg": "EdDSA", "typ": "JOSE", "kid": KID, "jku": "https://evil.example/keys"},
    ):
        raw = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b"=").decode()
        assert not is_valid_signature({**data, "sig": f"{raw}..{sig_part}"}, KEY.public_key())


def test_prev_hash_shape_and_stability() -> None:
    data = signed()
    first = prev_hash(data)
    assert len(first) == 64
    assert first == prev_hash(copy.deepcopy(data))
    assert first == prev_hash(Envelope.model_validate(data))


def test_prev_hash_changes_when_any_field_changes() -> None:
    data = {**signed(), "seq": 4, "ts": "2026-10-29T09:30:00Z", "prev_hash": "a" * 64}
    base = prev_hash(data)
    paths = list(leaves(data))
    assert len(paths) > 20
    for path in paths:
        assert prev_hash(mutated(data, path)) != base, path
    assert prev_hash({**data, "extra": 1}) != base
    assert prev_hash({k: v for k, v in data.items() if k != "causation_id"}) != base


def test_prev_hash_ignores_key_order_and_number_form() -> None:
    data = signed()
    reordered = dict(reversed(list(data.items())))
    assert prev_hash(reordered) == prev_hash(data)
    a = {**data, "payload": {"n": 200}}
    b = {**data, "payload": {"n": 200.0}}
    assert prev_hash(a) == prev_hash(b)
