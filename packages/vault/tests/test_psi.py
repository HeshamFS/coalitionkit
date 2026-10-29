# SPDX-License-Identifier: Apache-2.0
"""PSI correctness, authenticated transcript rejection, and relay observations."""

import base64
import json
import random
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coalitionkit_contracts.payloads import MatchPayload
from coalitionkit_contracts.validate import validate_payload
from coalitionkit_vault._group import hash_point
from coalitionkit_vault.canary import Canaries
from coalitionkit_vault.psi import (
    Context,
    CountNotAuthorized,
    DuplicateElement,
    LimitExceeded,
    PSIError,
    Requester,
    Responder,
    Reveal,
)
from coalitionkit_vault.store import Vault

ROOT = Path(__file__).resolve().parents[3]
TASK = "01M4XRC2A00000000000000002"
OTHER_TASK = "01M4XRC2A00000000000000003"


def parties(
    left: list[str],
    right: list[str],
    reveal: Reveal = "overlap",
    *,
    fixed: bool = False,
    context: Context | None = None,
) -> tuple[Requester, Responder]:
    # TEST ONLY signing seeds and scalars; production constructors randomize all scalars.
    alice = Ed25519PrivateKey.from_private_bytes(bytes([1]) * 32)
    bob = Ed25519PrivateKey.from_private_bytes(bytes([2]) * 32)
    ctx = context or Context("coalition-1", "match-1", "alice", "bob", reveal, TASK)
    return (
        Requester(
            ctx,
            left,
            alice,
            bob.public_key(),
            test_scalar=(3).to_bytes(32, "little") if fixed else None,
            test_channel_scalar=(5).to_bytes(32, "little") if fixed else None,
            test_order=fixed,
        ),
        Responder(
            ctx,
            right,
            bob,
            alice.public_key(),
            count_trusted=["alice"],
            test_scalar=(7).to_bytes(32, "little") if fixed else None,
            test_channel_scalar=(11).to_bytes(32, "little") if fixed else None,
            test_order=fixed,
        ),
    )


def exchange(left: list[str], right: list[str], reveal: Reveal) -> list[str] | int:
    requester, responder = parties(left, right, reveal)
    return requester.finish(responder.respond(requester.request(responder.setup())))


@pytest.mark.parametrize("reveal", ["overlap", "count"])
def test_sets(reveal: Reveal) -> None:
    samples: list[tuple[list[str], list[str]]] = [
        ([], []),
        (["a"], []),
        ([], ["b"]),
        (["a"], ["a"]),
        (["a"], ["b"]),
    ]
    rng = random.Random(5623)
    universe = [f"item-{i}" for i in range(200)]
    samples += [
        (rng.sample(universe, rng.randrange(100)), rng.sample(universe, rng.randrange(100)))
        for _ in range(15)
    ]
    samples += [
        (universe, universe),
        ([str(i) for i in range(1024)], [str(i) for i in range(512, 1536)]),
    ]
    for left, right in samples:
        overlap = sorted(set(left) & set(right))
        assert exchange(left, right, reveal) == (len(overlap) if reveal == "count" else overlap)


def test_limits() -> None:
    with pytest.raises(DuplicateElement):
        parties(["a", "a"], [])
    with pytest.raises(LimitExceeded):
        parties([str(i) for i in range(1025)], [])
    requester, responder = parties([], [])
    setup = responder.setup()
    with pytest.raises(LimitExceeded):
        requester.request(setup.model_copy(update={"blob": "A" * 94001}))


@pytest.mark.parametrize("round_index", [0, 1, 2])
def test_tamper(round_index: int) -> None:
    requester, responder = parties(["a", "b"], ["b", "c"])
    setup = responder.setup()

    def corrupt(payload: MatchPayload) -> MatchPayload:
        data = bytearray(base64.urlsafe_b64decode(payload.blob + "=" * (-len(payload.blob) % 4)))
        data[40], data[41] = data[41], data[40]
        data[42] ^= 1
        return payload.model_copy(
            update={
                "blob": base64.urlsafe_b64encode(data).rstrip(b"=").decode(),
            }
        )

    with pytest.raises(PSIError):
        if round_index == 0:
            requester.request(corrupt(setup))
        else:
            request = requester.request(setup)
            if round_index == 1:
                responder.respond(corrupt(request))
            else:
                requester.finish(corrupt(responder.respond(request)))


def test_context_round_and_replay() -> None:
    for ctx in (
        Context("other", "match-1", "alice", "bob", "overlap", TASK),
        Context("coalition-1", "other", "alice", "bob", "overlap", TASK),
        Context("coalition-1", "match-1", "bob", "alice", "overlap", TASK),
        Context("coalition-1", "match-1", "alice", "bob", "count", TASK),
    ):
        requester, _ = parties([], [], context=ctx)
        _, responder = parties([], [])
        with pytest.raises(PSIError):
            requester.request(responder.setup())
    requester, responder = parties(["a"], ["a"])
    setup = responder.setup()
    with pytest.raises(PSIError):
        responder.respond(setup)
    request = requester.request(setup)
    with pytest.raises(PSIError):
        requester.request(setup)
    response = responder.respond(request)
    assert requester.finish(response) == ["a"]
    with pytest.raises(PSIError):
        requester.finish(response)


def test_relay_and_canaries() -> None:
    vault = Vault("alice")
    canaries = Canaries.plant(vault, 20)
    recordings: list[list[bytes]] = []
    # Equal cardinalities with different intersections have identical wire lengths.
    for right in (["secret-b", "secret-c"], ["secret-c", "secret-d"]):
        requester, responder = parties(["secret-a", "secret-b"], right)
        setup = responder.setup()
        request = requester.request(setup)
        response = responder.respond(request)
        blobs = [
            base64.urlsafe_b64decode(p.blob + "=" * (-len(p.blob) % 4))
            for p in (setup, request, response)
        ]
        recordings.append(blobs)
        for blob in blobs:
            assert not canaries.scan(blob)
            for candidate in ["wrong-1", "wrong-2", "secret-a", *right]:
                assert candidate.encode() not in blob
                assert (
                    hash_point(requester.context.digest() + json.dumps(candidate).encode())
                    not in blob
                )
        assert requester.finish(response) == sorted({"secret-a", "secret-b"} & set(right))
    assert [len(b) for b in recordings[0]] == [len(b) for b in recordings[1]]
    assert all(a != b for a, b in zip(*recordings, strict=True))


def test_vectors() -> None:
    vector = json.loads((ROOT / "spec/vectors/psi.json").read_text())
    for reveal in ("overlap", "count"):
        requester, responder = parties(vector["left"], vector["right"], reveal, fixed=True)
        setup = responder.setup()
        request = requester.request(setup)
        response = responder.respond(request)
        for message in (setup, request, response):
            validate_payload("coalition.match", message.to_wire())
        assert [m.to_wire() for m in (setup, request, response)] == vector[reveal]["messages"]
        assert requester.finish(response) == vector[reveal]["result"]


def test_count_requires_count_trusted() -> None:
    alice = Ed25519PrivateKey.from_private_bytes(bytes([1]) * 32)
    bob = Ed25519PrivateKey.from_private_bytes(bytes([2]) * 32)
    count = Context("coalition-1", "match-1", "alice", "bob", "count", TASK)
    for trusted in ([], ["carol"]):
        with pytest.raises(CountNotAuthorized) as info:
            Responder(count, ["a"], bob, alice.public_key(), count_trusted=trusted)
        assert info.value.code == "not_authorized"
    overlap = Context("coalition-1", "match-1", "alice", "bob", "overlap", TASK)
    Responder(overlap, ["a"], bob, alice.public_key())  # overlap needs no listing
    Responder(count, ["a"], bob, alice.public_key(), count_trusted=["alice"])


def test_peer_binding() -> None:
    requester, responder = parties(["a"], ["a"])
    setup = responder.setup()
    assert setup.peer == "alice"
    with pytest.raises(PSIError):
        requester.request(setup.model_copy(update={"peer": "mallory"}))
    assert requester.request(setup).peer == "bob"


def test_reordered_blob() -> None:
    requester, responder = parties(["a", "b", "c"], ["b"])
    setup = responder.setup()
    request = requester.request(setup)
    raw = base64.urlsafe_b64decode(request.blob + "=" * (-len(request.blob) % 4))
    # Swap complete point-sized portions, keeping headers and lengths intact.
    reordered = raw[:71] + raw[105:139] + raw[71:105] + raw[139:]
    with pytest.raises(PSIError):
        responder.respond(
            request.model_copy(
                update={
                    "blob": base64.urlsafe_b64encode(reordered).rstrip(b"=").decode(),
                }
            )
        )


@pytest.mark.parametrize("point", [bytes(32), bytes([255]) * 32, bytes(31)])
def test_signed_invalid_setup(point: bytes) -> None:
    requester, _ = parties([], [])
    key = Ed25519PrivateKey.from_private_bytes(bytes([2]) * 32)
    raw = b"CKP1\x00" + requester.context.digest() + point
    raw += key.sign(raw)
    payload = MatchPayload(
        match_id="match-1",
        task_id=TASK,
        peer="alice",
        round="setup",
        reveal="overlap",
        blob=base64.urlsafe_b64encode(raw).rstrip(b"=").decode(),
    )
    with pytest.raises(PSIError):
        requester.request(payload)


def test_a_message_for_another_task_is_refused() -> None:
    requester, responder = parties(["a"], ["a"])
    setup = responder.setup()
    with pytest.raises(PSIError):
        requester.request(setup.model_copy(update={"task_id": OTHER_TASK}))
