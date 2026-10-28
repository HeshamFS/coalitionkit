# SPDX-License-Identifier: Apache-2.0
"""Authenticated idempotency: replay, duplicate_mismatch and the digest."""

from __future__ import annotations

import copy
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from examples import EVENT_ID, load_vector, make_envelope

from coalitionkit_contracts import (
    StoredSubmission,
    classify_submission,
    idempotency_key,
    sign_envelope,
    submission_digest,
)

KEY = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
SENDER = "https://agents.example.org/p2/card.json"


def signed() -> dict[str, Any]:
    env = make_envelope()
    env["sig"] = sign_envelope(env, KEY, "k1")
    return env


def stored(env: dict[str, Any]) -> StoredSubmission:
    return StoredSubmission(sender=SENDER, digest=submission_digest(env))


def test_key_is_coalition_and_event() -> None:
    assert idempotency_key(signed())[1] == EVENT_ID


def test_new_when_nothing_is_stored() -> None:
    assert classify_submission(None, SENDER, signed()) == "new"


def test_same_sender_same_bytes_is_a_replay_even_with_host_fields() -> None:
    env = signed()
    original = stored(env)
    assert classify_submission(original, SENDER, env) == "replay"
    accepted = {**env, "seq": 4, "ts": "2026-10-29T09:30:00Z", "prev_hash": "a" * 64}
    assert classify_submission(original, SENDER, accepted) == "replay"
    assert submission_digest(accepted) == submission_digest(env)


def test_other_authenticated_sender_is_a_mismatch() -> None:
    env = signed()
    other = "https://agents.example.org/p9/card.json"
    assert classify_submission(stored(env), other, env) == "mismatch"


def test_changed_envelope_is_a_mismatch() -> None:
    env = signed()
    original = stored(env)
    changed = copy.deepcopy(env)
    changed["payload"]["capacity"] = 3
    assert classify_submission(original, SENDER, changed) == "mismatch"
    resigned = {**changed, "sig": sign_envelope(changed, KEY, "k2")}
    assert classify_submission(original, SENDER, resigned) == "mismatch"
    assert classify_submission(original, SENDER, {**env, "sig": "x..y"}) == "mismatch"
    assert classify_submission(original, SENDER, {**env, "scope": {"audience": "host"}}) == (
        "mismatch"
    )


def test_digest_ignores_key_order_and_number_form() -> None:
    env = signed()
    assert submission_digest(dict(reversed(list(env.items())))) == submission_digest(env)
    a = {**env, "payload": {"n": 200}}
    b = {**env, "payload": {"n": 200.0}}
    assert submission_digest(a) == submission_digest(b)


def test_digest_vector() -> None:
    vector = load_vector("signing.json")
    expected = vector["submission_digest_of_accepted"]
    assert submission_digest(vector["envelope_accepted_by_host"]) == expected
    assert submission_digest(vector["envelope_signed"]) == expected
