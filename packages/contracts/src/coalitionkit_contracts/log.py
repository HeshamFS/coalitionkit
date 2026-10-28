# SPDX-License-Identifier: Apache-2.0
"""The authenticated log boundary: genesis hash, hash chain checks and host-signed receipts.

``prev_hash`` of seq 1 is the SHA-256 of the JCS form of
``{coalition_id, host_card_url, created_at}``. Every acknowledgement carries a host-signed
``coalition.receipt`` ``{coalition_id, seq, head_hash}`` where ``head_hash`` is the SHA-256 of the
JCS form of the accepted envelope at ``seq`` (the value the next ``prev_hash`` must hold). A member
that keeps its receipts can therefore detect an edited or truncated tail.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .canonical import canonicalize, envelope_dict, prev_hash, sha256_hex
from .envelope import Envelope
from .signing import SignatureError, verify_envelope

Kind = Literal["bad_genesis", "gap", "broken_chain", "truncated", "receipt_mismatch"]


class LogIntegrityError(Exception):
    """The log does not match its genesis, its own chain or a receipt the host signed."""

    def __init__(self, kind: Kind, detail: str) -> None:
        super().__init__(f"{kind}: {detail}")
        self.kind: Kind = kind


@dataclass(frozen=True)
class LogStub:
    """A replay entry for an event outside the reader's scope: only its place in the chain."""

    seq: int
    prev_hash: str
    hash: str


@dataclass(frozen=True)
class ReceiptInfo:
    seq: int
    head_hash: str


Entry = Envelope | Mapping[str, Any] | LogStub


def genesis_hash(coalition_id: str, host_card_url: str, created_at: str) -> str:
    """The ``prev_hash`` of seq 1."""
    return sha256_hex(
        canonicalize(
            {"coalition_id": coalition_id, "host_card_url": host_card_url, "created_at": created_at}
        )
    )


def _seq(entry: Entry) -> int:
    value = entry.seq if isinstance(entry, LogStub) else envelope_dict(entry).get("seq")
    if not isinstance(value, int):
        raise LogIntegrityError("gap", "an entry has no seq")
    return value


def _prev(entry: Entry) -> object:
    return entry.prev_hash if isinstance(entry, LogStub) else envelope_dict(entry).get("prev_hash")


def entry_hash(entry: Entry) -> str:
    """The hash the next entry must carry as ``prev_hash``."""
    return entry.hash if isinstance(entry, LogStub) else prev_hash(entry)


def verify_chain(entries: Sequence[Entry], genesis: str, *, first_seq: int = 1) -> int:
    """Check seq is gap-free from ``first_seq`` and each ``prev_hash`` links to the one before.

    ``genesis`` is the expected ``prev_hash`` of ``entries[0]`` (the genesis hash for a full
    replay). Returns the head seq (``first_seq - 1`` for an empty log).
    """
    expected_prev = genesis
    expected_seq = first_seq
    for entry in entries:
        if _seq(entry) != expected_seq:
            raise LogIntegrityError("gap", f"expected seq {expected_seq}, found {_seq(entry)}")
        if _prev(entry) != expected_prev:
            kind: Kind = "bad_genesis" if expected_seq == 1 else "broken_chain"
            raise LogIntegrityError(kind, f"prev_hash at seq {expected_seq} does not link")
        expected_prev = entry_hash(entry)
        expected_seq += 1
    return expected_seq - 1


def receipt_payload(coalition_id: str, accepted: Envelope | Mapping[str, Any]) -> dict[str, Any]:
    """The payload of the receipt for an accepted envelope (which carries its host fields)."""
    seq = envelope_dict(accepted).get("seq")
    if not isinstance(seq, int):
        raise ValueError("the accepted envelope has no seq")
    return {"coalition_id": coalition_id, "seq": seq, "head_hash": prev_hash(accepted)}


def verify_receipt(
    receipt: Envelope | Mapping[str, Any],
    host_public_key: Ed25519PublicKey,
    *,
    accepted: Envelope | Mapping[str, Any] | None = None,
    expected_kid: str | None = None,
) -> ReceiptInfo:
    """Verify a receipt envelope against the pinned host key and, if given, the accepted envelope.

    Raises SignatureError for a bad signature and LogIntegrityError for a receipt that does not
    describe ``accepted``.
    """
    data = envelope_dict(receipt)
    verify_envelope(data, host_public_key, expected_kid=expected_kid)
    body: Any = data.get("payload")
    if data.get("type") != "coalition.receipt" or not isinstance(body, Mapping):
        raise SignatureError("not a coalition.receipt envelope")
    payload: Mapping[str, Any] = body  # pyright: ignore[reportUnknownVariableType]
    seq, head = payload.get("seq"), payload.get("head_hash")
    if payload.get("coalition_id") != data.get("coalition_id") or not isinstance(seq, int):
        raise LogIntegrityError("receipt_mismatch", "receipt names another Coalition")
    if not isinstance(head, str):
        raise LogIntegrityError("receipt_mismatch", "receipt has no head_hash")
    if accepted is not None:
        acc = envelope_dict(accepted)
        if acc.get("coalition_id") != data.get("coalition_id") or acc.get("seq") != seq:
            raise LogIntegrityError("receipt_mismatch", "receipt is for another event")
        if prev_hash(acc) != head:
            raise LogIntegrityError("receipt_mismatch", "head_hash differs from the envelope")
    return ReceiptInfo(seq=seq, head_hash=head)


def check_receipts(entries: Sequence[Entry], receipts: Sequence[ReceiptInfo]) -> None:
    """Compare a replayed log with the receipts a member kept.

    ``truncated``: the log ends before a receipt's seq. ``receipt_mismatch``: the entry at a
    receipt's seq hashes to something else (an edited tail, even one with a re-linked chain).
    """
    if not entries:
        if receipts:
            raise LogIntegrityError("truncated", "the log is empty but receipts exist")
        return
    first, head = _seq(entries[0]), _seq(entries[-1])
    for receipt in receipts:
        if receipt.seq > head:
            raise LogIntegrityError(
                "truncated", f"log ends at {head}, receipt is for {receipt.seq}"
            )
        if receipt.seq < first:
            continue
        if entry_hash(entries[receipt.seq - first]) != receipt.head_hash:
            raise LogIntegrityError("receipt_mismatch", f"entry {receipt.seq} was changed")
