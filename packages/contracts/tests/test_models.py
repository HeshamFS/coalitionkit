# SPDX-License-Identifier: Apache-2.0
"""Every message type passes the model and the JSON Schema when valid, and fails both when not."""

from __future__ import annotations

import copy
import json
from collections.abc import Iterator
from typing import Any, cast

import pytest
from examples import PAYLOADS, PLAN_ID, SCOPE, TASK_ID, make_envelope
from pydantic import ValidationError

from coalitionkit_contracts import (
    HOST_ONLY_TYPES,
    MEMBER_TYPES,
    MESSAGE_TYPES,
    PAYLOAD_MODELS,
    Envelope,
    SchemaValidationError,
    Scope,
    validate_envelope,
    validate_payload,
    validate_scope,
)
from coalitionkit_contracts.validate import SCHEMA_FILES, load_schemas

TYPES = sorted(PAYLOADS)
BASE = "https://coalitionkit.dev/schemas/coalition/v0/"


def required_of(message_type: str) -> list[str]:
    return list(load_schemas()[f"{BASE}{SCHEMA_FILES[message_type]}.json"]["required"])


def model_accepts(message_type: str, payload: Any) -> bool:
    try:
        PAYLOAD_MODELS[message_type].model_validate(payload)
    except ValidationError:
        return False
    return True


def schema_accepts(message_type: str, payload: Any) -> bool:
    try:
        validate_payload(message_type, payload)
    except SchemaValidationError:
        return False
    return True


def dict_paths(value: Any, path: tuple[Any, ...] = ()) -> Iterator[tuple[Any, ...]]:
    """Paths to every object inside ``value``, the root included."""
    if isinstance(value, dict):
        yield path
        for key, child in cast("dict[str, Any]", value).items():
            yield from dict_paths(child, (*path, key))
    elif isinstance(value, list):
        for index, child in enumerate(cast("list[Any]", value)):
            yield from dict_paths(child, (*path, index))


def at(value: Any, path: tuple[Any, ...]) -> Any:
    for step in path:
        value = value[step]
    return value


def test_eighteen_types_and_every_schema_exists() -> None:
    assert len(MESSAGE_TYPES) == 18
    assert set(MESSAGE_TYPES) == HOST_ONLY_TYPES | MEMBER_TYPES
    assert not HOST_ONLY_TYPES & MEMBER_TYPES
    assert len(HOST_ONLY_TYPES) == 8
    assert set(PAYLOAD_MODELS) == set(PAYLOADS) == set(SCHEMA_FILES)
    ids = set(load_schemas())
    for name in [*SCHEMA_FILES.values(), "envelope", "scope", "common"]:
        assert f"{BASE}{name}.json" in ids


@pytest.mark.parametrize("message_type", TYPES)
def test_valid_example_passes_both(message_type: str) -> None:
    assert model_accepts(message_type, PAYLOADS[message_type])
    assert schema_accepts(message_type, PAYLOADS[message_type])


@pytest.mark.parametrize("message_type", TYPES)
def test_round_trip(message_type: str) -> None:
    model = PAYLOAD_MODELS[message_type]
    parsed = model.model_validate(PAYLOADS[message_type])
    assert parsed.to_wire() == PAYLOADS[message_type]
    assert model.model_validate_json(json.dumps(PAYLOADS[message_type])) == parsed
    assert model.model_validate(parsed.to_wire()) == parsed


@pytest.mark.parametrize("message_type", TYPES)
def test_extra_field_fails_both_at_every_level(message_type: str) -> None:
    example = PAYLOADS[message_type]
    for path in dict_paths(example):
        if path and path[-1] == "objective_scores":
            continue  # an open map of objective name to score, not a fixed shape
        if message_type == "coalition.projection" and path == ("payload",):
            continue  # the projected payload is an open object by design
        bad = copy.deepcopy(example)
        at(bad, path)["unexpected"] = 1
        assert not model_accepts(message_type, bad), path
        assert not schema_accepts(message_type, bad), path


@pytest.mark.parametrize("message_type", TYPES)
def test_missing_required_field_fails_both(message_type: str) -> None:
    for field in required_of(message_type):
        bad = {k: v for k, v in PAYLOADS[message_type].items() if k != field}
        assert not model_accepts(message_type, bad), field
        assert not schema_accepts(message_type, bad), field


@pytest.mark.parametrize("message_type", TYPES)
def test_null_fails_both(message_type: str) -> None:
    for field in PAYLOADS[message_type]:
        bad = {**PAYLOADS[message_type], field: None}
        assert not model_accepts(message_type, bad), field
        assert not schema_accepts(message_type, bad), field


@pytest.mark.parametrize("message_type", TYPES)
def test_optional_fields_may_be_omitted(message_type: str) -> None:
    required = required_of(message_type)
    minimal = {k: v for k, v in PAYLOADS[message_type].items() if k in required}
    assert model_accepts(message_type, minimal)
    assert schema_accepts(message_type, minimal)


BAD_VALUES: list[tuple[str, dict[str, Any]]] = [
    ("coalition.offer", {"capacity": 0}),
    ("coalition.offer", {"capacity": 1.5}),
    ("coalition.offer", {"capacity": True}),
    ("coalition.offer", {"cost": {"minutes": 1, "money": 1.5, "effort": "low"}}),
    ("coalition.offer", {"cost": {"minutes": 1, "money": -1, "effort": "low"}}),
    ("coalition.offer", {"cost": {"minutes": 1, "money": 2**53, "effort": "low"}}),
    ("coalition.offer", {"cost": {"minutes": 1, "money": 1, "effort": "so-so"}}),
    ("coalition.offer", {"valid_until": "tomorrow"}),
    ("coalition.offer", {"valid_until": "2026-11-02 18:00:00Z"}),
    ("coalition.offer", {"target": {"kind": "plan", "id": "x"}}),
    ("coalition.join", {"vault": "cloud"}),
    ("coalition.join", {"card_url": "not a uri"}),
    ("coalition.join", {"roles_requested": ["a", "a"]}),
    ("coalition.observe", {"source": "telepathy"}),
    ("coalition.query", {"deadline_ms": 0}),
    ("coalition.answer", {"result": "maybe"}),
    ("coalition.match", {"round": "final"}),
    ("coalition.match", {"blob": "not base64url!"}),
    ("coalition.decide", {"subject": {"kind": "plan", "id": PLAN_ID, "revision": 0}}),
    ("coalition.decide", {"subject": {"kind": "plan", "id": PLAN_ID}}),
    ("coalition.decide", {"subject": {"kind": "plan", "id": "plan-a", "revision": 1}}),
    ("coalition.decide", {"subject": {"kind": "offer", "id": PLAN_ID, "revision": 1}}),
    ("coalition.decide", {"consent": "yes"}),
    ("coalition.decide", {"consent_sig": "eyJhbGciOiJFZERTQSJ9.cGF5.c2ln"}),
    ("coalition.decide", {"consent_sig": ""}),
    ("coalition.decide", {"decided_at": "yesterday"}),
    ("coalition.commit", {"status": "done"}),
    ("coalition.commit", {"status": "approved"}),
    ("coalition.commit", {"task_id": "t-1"}),
    ("coalition.commit", {"revision": 0}),
    ("coalition.join", {"owner_proof": "eyJhbGciOiJFZERTQSJ9.cGF5.c2ln"}),
    ("coalition.join", {"owner_key": {"kty": "RSA", "crv": "Ed25519", "x": "A" * 43, "kid": "k"}}),
    ("coalition.join", {"owner_key": {"kty": "OKP", "crv": "Ed25519", "x": "short", "kid": "k"}}),
    ("coalition.join", {"owner_key": {"kty": "OKP", "crv": "Ed25519", "x": "A" * 43}}),
    ("coalition.match", {"blob": "A" * 87_393}),
    ("coalition.match", {"peer": ""}),
    ("coalition.charter", {"deciders": []}),
    ("coalition.charter", {"revision": 0}),
    ("coalition.charter", {"created_at": "today"}),
    ("coalition.tension", {"tension_id": "tn-1"}),
    (
        "coalition.propose",
        {
            "plans": [
                {"plan_id": "plan-a", "revision": 1, "assignments": [], "objective_scores": {}}
            ]
        },
    ),
    (
        "coalition.propose",
        {
            "plans": [
                {
                    "plan_id": PLAN_ID,
                    "revision": 1,
                    "assignments": [{"task_id": "t-1", "assignee": "p2"}],
                    "objective_scores": {},
                }
            ]
        },
    ),
    ("coalition.need", {"need_id": "n-1"}),
    ("coalition.offer", {"target": {"kind": "need", "id": "n-1"}}),
    ("coalition.done", {"task_id": "t-1"}),
    ("coalition.ripple", {"invalidates": ["t-1"]}),
    ("coalition.ripple", {"invalidates": [TASK_ID, TASK_ID]}),
    ("coalition.error", {"code": "duplicate"}),
    (
        "coalition.projection",
        {"source": {"event_id": "x", "seq": 7, "type": "coalition.need", "on_behalf_of": "host"}},
    ),
    (
        "coalition.projection",
        {
            "source": {
                "event_id": PLAN_ID,
                "seq": 0,
                "type": "coalition.need",
                "on_behalf_of": "host",
            }
        },
    ),
    (
        "coalition.projection",
        {"source": {"event_id": PLAN_ID, "seq": 1, "type": "need", "on_behalf_of": "host"}},
    ),
    ("coalition.projection", {"payload": []}),
    ("coalition.projection", {"redacted": ["window"]}),
    ("coalition.projection", {"redacted": ["payload.a", "payload.a"]}),
    ("coalition.receipt", {"head_hash": "AB" * 32}),
    ("coalition.receipt", {"head_hash": "ab" * 31}),
    ("coalition.receipt", {"seq": 0}),
    ("coalition.receipt", {"coalition_id": "c-1"}),
    ("coalition.dissolve", {"reason": "bored"}),
    ("coalition.error", {"code": "oops"}),
    ("coalition.error", {"ref": "not-a-ulid"}),
    ("coalition.tension", {"deciders": []}),
    ("coalition.tension", {"options": [{"option_id": "a", "summary": "only one"}]}),
    ("coalition.propose", {"plans": []}),
    ("coalition.charter", {"budget": {"amount": 1.5, "currency": "EUR"}}),
    ("coalition.charter", {"budget": {"amount": 100, "currency": "euro"}}),
    ("coalition.charter", {"roles": []}),
    ("coalition.need", {"window": {"start": "2026-11-02T09:00:00Z"}}),
    ("coalition.ripple", {"invalidates": "t-1"}),
    ("coalition.done", {"evidence": [{"kind": "document", "ref": "doc-9"}]}),
]


@pytest.mark.parametrize(("message_type", "change"), BAD_VALUES)
def test_bad_values_fail_both(message_type: str, change: dict[str, Any]) -> None:
    bad = {**PAYLOADS[message_type], **change}
    assert not model_accepts(message_type, bad)
    assert not schema_accepts(message_type, bad)


def test_query_deadline_is_optional_with_a_default() -> None:
    from coalitionkit_contracts.payloads import DEFAULT_QUERY_DEADLINE_MS, QueryPayload

    payload = {"query_id": "q-1", "kind": "cost", "subject": "n-1"}
    assert model_accepts("coalition.query", payload)
    assert schema_accepts("coalition.query", payload)
    assert QueryPayload.model_validate(payload).deadline_ms == DEFAULT_QUERY_DEADLINE_MS == 10_000


@pytest.mark.parametrize("kind", ["plan", "tension_option", "commitment", "charter", "task"])
def test_every_subject_kind_passes_both(kind: str) -> None:
    subject = {"kind": kind, "id": PLAN_ID, "revision": 4}
    payload = {**PAYLOADS["coalition.decide"], "subject": subject}
    assert model_accepts("coalition.decide", payload)
    assert schema_accepts("coalition.decide", payload)


def test_new_error_codes_pass_both() -> None:
    for code in ("duplicate_mismatch", "not_authorized"):
        payload = {**PAYLOADS["coalition.error"], "code": code}
        assert model_accepts("coalition.error", payload)
        assert schema_accepts("coalition.error", payload)


def test_projection_payload_is_open_but_the_rest_is_closed() -> None:
    payload = {**PAYLOADS["coalition.projection"], "payload": {"anything": {"nested": [1, 2]}}}
    assert model_accepts("coalition.projection", payload)
    assert schema_accepts("coalition.projection", payload)


def test_answer_accepts_yes_and_no() -> None:
    for result in ("yes", "no"):
        payload = {"query_id": "q-1", "result": result}
        assert model_accepts("coalition.answer", payload)
        assert schema_accepts("coalition.answer", payload)


@pytest.mark.parametrize("audience", ["coalition", "roles", "participants", "self", "host"])
def test_scope_audiences(audience: str) -> None:
    scope: dict[str, Any] = {"audience": audience}
    if audience == "roles":
        scope["roles"] = ["organizer"]
    if audience == "participants":
        scope["participants"] = ["p1"]
    validate_scope(scope)
    assert Scope.model_validate(scope).to_wire() == scope


@pytest.mark.parametrize(
    "scope",
    [
        {},
        {"audience": "everyone"},
        {"audience": "participants"},
        {"audience": "participants", "participants": []},
        {"audience": "roles", "roles": []},
        {"audience": "self", "extra": 1},
        {"audience": "self", "redact": ["window"]},
        {"audience": "self", "participants": ["p1", "p1"]},
    ],
)
def test_bad_scope_fails_both(scope: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        Scope.model_validate(scope)
    with pytest.raises(SchemaValidationError):
        validate_scope(scope)


def test_scope_example_round_trips() -> None:
    validate_scope(SCOPE)
    assert Scope.model_validate(SCOPE).to_wire() == SCOPE


@pytest.mark.parametrize("message_type", TYPES)
def test_envelope_round_trip_and_both_validate(message_type: str) -> None:
    data = make_envelope(message_type)
    validate_envelope(data)
    envelope = Envelope.model_validate(data)
    assert envelope.to_wire() == data
    assert Envelope.model_validate_json(json.dumps(data)) == envelope
    assert envelope.parse_payload().to_wire() == PAYLOADS[message_type]


def test_envelope_with_host_fields_round_trips() -> None:
    data = make_envelope(seq=3, ts="2026-10-29T09:30:00.250Z", prev_hash="ab" * 32)
    validate_envelope(data)
    assert Envelope.model_validate(data).to_wire() == data


ENVELOPE_CHANGES: list[dict[str, Any]] = [
    {"ext_version": "0.2"},
    {"coalition_id": "short"},
    {"event_id": "01M4XRC0Z8185GR38E1W8124Gk"},
    {"type": "Coalition.Offer"},
    {"type": "offer"},
    {"sender": "not a url"},
    {"scope": {}},
    {"seq": 0},
    {"ts": "yesterday"},
    {"prev_hash": "ABC"},
    {"extra": True},
    {"payload": []},
    {"causation_id": "x"},
]


@pytest.mark.parametrize("change", ENVELOPE_CHANGES)
def test_bad_envelope_fails_both(change: dict[str, Any]) -> None:
    data = make_envelope(**change)
    with pytest.raises(ValidationError):
        Envelope.model_validate(data)
    with pytest.raises(SchemaValidationError):
        validate_envelope(data)


@pytest.mark.parametrize("field", ["sender", "on_behalf_of", "scope", "payload", "sig", "type"])
def test_missing_envelope_field_fails_both(field: str) -> None:
    data = {k: v for k, v in make_envelope().items() if k != field}
    with pytest.raises(ValidationError):
        Envelope.model_validate(data)
    with pytest.raises(SchemaValidationError):
        validate_envelope(data)


def test_envelope_payload_is_checked_by_type() -> None:
    data = make_envelope("coalition.offer", payload={**PAYLOADS["coalition.offer"], "x": 1})
    with pytest.raises(SchemaValidationError):
        validate_envelope(data)
    with pytest.raises(ValidationError):
        Envelope.model_validate(data).parse_payload()


def test_unknown_type_is_rejected() -> None:
    data = make_envelope(type="coalition.bogus")
    with pytest.raises(SchemaValidationError):
        validate_envelope(data)
    with pytest.raises(ValueError, match="unknown message type"):
        Envelope.model_validate(data).parse_payload()
    with pytest.raises(SchemaValidationError):
        validate_payload("coalition.bogus", {})
