# SPDX-License-Identifier: Apache-2.0
"""Genesis hash, hash chain, receipts, tail edits and truncation."""

from __future__ import annotations

import copy
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from examples import load_vector, make_envelope

from coalitionkit_contracts import (
    LogIntegrityError,
    LogStub,
    ReceiptInfo,
    SignatureError,
    canonicalize,
    check_receipts,
    entry_hash,
    genesis_hash,
    prev_hash,
    receipt_payload,
    sha256_hex,
    sign_envelope,
    validate_envelope,
    verify_chain,
    verify_receipt,
)

LOG = load_vector("log.json")
ENTRIES: list[dict[str, Any]] = LOG["entries"]
RECEIPTS: list[dict[str, Any]] = LOG["receipts"]
GENESIS: str = LOG["genesis"]["hash"]
HOST = Ed25519PublicKey.from_public_bytes(bytes.fromhex(LOG["host_key"]["public_key_hex"]))
INFOS = [ReceiptInfo(r["payload"]["seq"], r["payload"]["head_hash"]) for r in RECEIPTS]


def failure_kind(entries: list[Any]) -> str:
    """Replay: chain first, then the receipts. Returns the kind of the first failure."""
    with pytest.raises(LogIntegrityError) as info:
        verify_chain(entries, GENESIS, HOST)
        check_receipts(entries, INFOS, HOST)
    return info.value.kind


def test_genesis_hash_is_sha256_of_jcs() -> None:
    g = LOG["genesis"]
    data = {k: g[k] for k in ("coalition_id", "host_card_url", "created_at")}
    assert canonicalize(data).decode() == g["canonical_utf8"]
    assert genesis_hash(**data) == g["hash"] == sha256_hex(canonicalize(data))
    assert genesis_hash(g["coalition_id"], g["host_card_url"] + "x", g["created_at"]) != g["hash"]
    assert genesis_hash(g["coalition_id"], g["host_card_url"], "2026-10-29T08:00:01Z") != g["hash"]


def test_the_good_log_verifies_end_to_end() -> None:
    assert ENTRIES[0]["prev_hash"] == GENESIS
    assert verify_chain(ENTRIES, GENESIS, HOST) == 4
    check_receipts(ENTRIES, INFOS, HOST)
    assert [entry_hash(e) for e in ENTRIES] == LOG["head_hashes"]
    for entry, receipt in zip(ENTRIES, RECEIPTS, strict=True):
        validate_envelope(entry)
        validate_envelope(receipt)
        assert receipt["payload"] == receipt_payload(entry["coalition_id"], entry)
        info = verify_receipt(receipt, HOST, accepted=entry, expected_kid="host-key-1")
        assert info.head_hash == prev_hash(entry)


def test_wrong_genesis_is_detected() -> None:
    with pytest.raises(LogIntegrityError) as info:
        verify_chain(ENTRIES, "0" * 64, HOST)
    assert info.value.kind == "bad_genesis"


def test_a_gap_is_detected() -> None:
    assert failure_kind([ENTRIES[0], ENTRIES[2], ENTRIES[3]]) == "gap"


def test_an_edit_before_the_tail_breaks_the_chain() -> None:
    entries = copy.deepcopy(ENTRIES)
    entries[1]["payload"]["reason"] = "edited"
    assert failure_kind(entries) == "broken_chain"


def test_a_tail_edit_is_caught_by_the_receipt_even_with_a_valid_chain() -> None:
    entries = copy.deepcopy(ENTRIES)
    entries[-1]["payload"]["reason"] = "edited tail"
    assert verify_chain(entries, GENESIS, HOST) == 4  # the chain alone cannot see it
    assert failure_kind(entries) == "receipt_mismatch"


def test_an_edit_with_a_relinked_chain_is_caught() -> None:
    entries = copy.deepcopy(ENTRIES)
    entries[2]["payload"]["reason"] = "edited"
    entries[3]["prev_hash"] = prev_hash(entries[2])
    assert verify_chain(entries, GENESIS, HOST) == 4
    assert failure_kind(entries) == "receipt_mismatch"


@pytest.mark.parametrize("keep", [0, 1, 2, 3])
def test_truncation_is_detected(keep: int) -> None:
    entries = ENTRIES[:keep]
    assert verify_chain(entries, GENESIS, HOST) == keep
    assert failure_kind(entries) == "truncated"


def test_a_member_can_only_detect_what_its_receipts_cover() -> None:
    check_receipts(ENTRIES[:2], INFOS[:2], HOST)


def test_stubs_keep_the_chain_checkable() -> None:
    mixed: list[Any] = [
        LogStub(e["seq"], e["prev_hash"], prev_hash(e)) if i % 2 else e
        for i, e in enumerate(ENTRIES)
    ]
    assert verify_chain(mixed, GENESIS, HOST) == 4
    check_receipts(mixed, INFOS, HOST)
    mixed[1] = LogStub(2, ENTRIES[1]["prev_hash"], "f" * 64)
    assert failure_kind(mixed) == "broken_chain"


def test_partial_replay_from_an_anchor() -> None:
    assert verify_chain(ENTRIES[2:], prev_hash(ENTRIES[1]), HOST, first_seq=3) == 4
    check_receipts(ENTRIES[2:], INFOS, HOST)


def test_receipt_signature_and_binding() -> None:
    receipt, entry = RECEIPTS[0], ENTRIES[0]
    other = Ed25519PrivateKey.from_private_bytes(bytes(range(32))).public_key()
    with pytest.raises(SignatureError):
        verify_receipt(receipt, other)
    forged = copy.deepcopy(receipt)
    forged["payload"]["head_hash"] = "0" * 64
    with pytest.raises(SignatureError):
        verify_receipt(forged, HOST)
    with pytest.raises(LogIntegrityError):
        verify_receipt(RECEIPTS[1], HOST, accepted=entry)
    edited = {**entry, "payload": {"reason": "edited"}}
    with pytest.raises(LogIntegrityError):
        verify_receipt(receipt, HOST, accepted=edited)


def test_a_receipt_signed_by_a_member_key_does_not_verify_as_the_host() -> None:
    member = Ed25519PrivateKey.from_private_bytes(bytes(range(1, 33)))
    fake = copy.deepcopy(RECEIPTS[0])
    fake["sig"] = sign_envelope(fake, member, "host-key-1")
    with pytest.raises(SignatureError):
        verify_receipt(fake, HOST)


def test_receipt_needs_the_receipt_type_and_matching_coalition() -> None:
    host = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(LOG["host_key"]["private_seed_hex"]))
    not_receipt = make_envelope("coalition.leave")
    not_receipt["sig"] = sign_envelope(not_receipt, host, "host-key-1")
    with pytest.raises(SignatureError):
        verify_receipt(not_receipt, HOST)
    wrong = copy.deepcopy(RECEIPTS[0])
    wrong["payload"]["coalition_id"] = "01M4XRC000000G40R40M30E20A"
    wrong["sig"] = sign_envelope(wrong, host, "host-key-1")
    with pytest.raises(LogIntegrityError):
        verify_receipt(wrong, HOST)


def test_empty_log_with_receipts_is_truncated() -> None:
    with pytest.raises(LogIntegrityError):
        check_receipts([], INFOS, HOST)
    check_receipts([], [], HOST)
