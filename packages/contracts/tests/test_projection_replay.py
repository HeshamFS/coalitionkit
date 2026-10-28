# SPDX-License-Identifier: Apache-2.0
"""A replay that holds host-signed projections still verifies the hash chain and receipts."""

from __future__ import annotations

import copy
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from examples import load_vector, make_envelope

from coalitionkit_contracts import (
    LogIntegrityError,
    ReceiptInfo,
    SignatureError,
    check_receipts,
    entry_hash,
    prev_hash,
    projection_stub,
    sign_envelope,
    verify_chain,
    verify_projection,
)

LOG = load_vector("log.json")
ENTRIES: list[dict[str, Any]] = LOG["entries"]
GENESIS: str = LOG["genesis"]["hash"]
HOST_KEY = Ed25519PrivateKey.from_private_bytes(bytes([9]) * 32)
KID = "host-1"


def project(entry: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "source": {
            "event_id": entry["event_id"],
            "seq": entry["seq"],
            "type": entry["type"],
            "on_behalf_of": entry["on_behalf_of"],
            "prev_hash": entry["prev_hash"],
            "hash": prev_hash(entry),
        },
        "payload": {},
        "redacted": ["payload.content"],
    }
    unsigned = make_envelope(
        "coalition.projection",
        sender="https://host.example.org/card.json",
        on_behalf_of="host",
        scope={"audience": "participants", "participants": ["p2"]},
        payload=payload,
    )
    unsigned["sig"] = sign_envelope(unsigned, HOST_KEY, KID)
    return unsigned


def resign(projection: dict[str, Any]) -> dict[str, Any]:
    body = {k: v for k, v in projection.items() if k != "sig"}
    return {**body, "sig": sign_envelope(body, HOST_KEY, KID)}


INFOS = [ReceiptInfo(r["payload"]["seq"], r["payload"]["head_hash"]) for r in LOG["receipts"]]


def forgeries() -> list[dict[str, Any]]:
    edited = copy.deepcopy(project(ENTRIES[1]))
    edited["payload"]["payload"]["injected"] = "x"  # payload edited after signing
    rehashed = copy.deepcopy(project(ENTRIES[1]))
    rehashed["payload"]["source"]["hash"] = "1" * 64  # source metadata edited after signing
    wrong_key = copy.deepcopy(project(ENTRIES[1]))
    other = Ed25519PrivateKey.from_private_bytes(bytes([8]) * 32)
    body = {k: v for k, v in wrong_key.items() if k != "sig"}
    wrong_key["sig"] = sign_envelope(body, other, KID)
    return [edited, rehashed, wrong_key]


@pytest.mark.parametrize("forged", range(3))
def test_a_forged_projection_fails_chain_and_receipt_checks(forged: int) -> None:
    mixed: list[Any] = [ENTRIES[0], forgeries()[forged], *ENTRIES[2:]]
    key = HOST_KEY.public_key()
    with pytest.raises(SignatureError):
        verify_chain(mixed, GENESIS, key)
    with pytest.raises(SignatureError):
        check_receipts(mixed, INFOS, key)


def test_a_projection_signed_for_another_kid_is_refused() -> None:
    mixed: list[Any] = [ENTRIES[0], project(ENTRIES[1]), *ENTRIES[2:]]
    with pytest.raises(SignatureError):
        verify_chain(mixed, GENESIS, HOST_KEY.public_key(), expected_kid="other-kid")


def test_entry_hash_refuses_an_unverified_projection() -> None:
    with pytest.raises(ValueError, match="verify the projection"):
        entry_hash(project(ENTRIES[1]))


def test_projection_carries_the_chain_metadata_of_its_source() -> None:
    projection = project(ENTRIES[1])
    stub = projection_stub(projection)
    assert (stub.seq, stub.prev_hash, stub.hash) == (
        ENTRIES[1]["seq"],
        ENTRIES[1]["prev_hash"],
        prev_hash(ENTRIES[1]),
    )
    assert verify_projection(projection, HOST_KEY.public_key(), expected_kid=KID) == stub


def test_chain_and_receipts_verify_with_projections_in_place_of_originals() -> None:
    mixed: list[Any] = [project(e) if i % 2 else e for i, e in enumerate(ENTRIES)]
    assert verify_chain(mixed, GENESIS, HOST_KEY.public_key()) == len(ENTRIES)
    infos = [ReceiptInfo(r["payload"]["seq"], r["payload"]["head_hash"]) for r in LOG["receipts"]]
    check_receipts(mixed, infos, HOST_KEY.public_key())


def test_a_projection_with_a_wrong_source_prev_hash_breaks_the_chain() -> None:
    bad = copy.deepcopy(project(ENTRIES[1]))
    bad["payload"]["source"]["prev_hash"] = "0" * 64
    mixed: list[Any] = [ENTRIES[0], resign(bad), *ENTRIES[2:]]
    with pytest.raises(LogIntegrityError):
        verify_chain(mixed, GENESIS, HOST_KEY.public_key())


def test_a_projection_must_verify_against_the_host_key() -> None:
    projection = project(ENTRIES[1])
    other = Ed25519PrivateKey.from_private_bytes(bytes([8]) * 32).public_key()
    with pytest.raises(SignatureError):
        verify_projection(projection, other)
    tampered = copy.deepcopy(projection)
    tampered["payload"]["source"]["hash"] = "1" * 64
    with pytest.raises(SignatureError):
        verify_projection(tampered, HOST_KEY.public_key())


def test_projection_hash_is_not_the_chain_hash() -> None:
    projection = project(ENTRIES[1])
    assert prev_hash(projection) != prev_hash(ENTRIES[1])


def test_a_non_projection_has_no_stub() -> None:
    with pytest.raises(ValueError, match="projection"):
        projection_stub(ENTRIES[0])
