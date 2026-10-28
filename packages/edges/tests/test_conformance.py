# SPDX-License-Identifier: Apache-2.0
"""Member and edge conformance over a real port (C-01 to C-05, C-14) and the A2A refusals."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

import httpx
import pytest
from a2a.types import AgentCard, Message, Part, Role, SendMessageRequest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from examples import COALITION_ID
from google.protobuf.json_format import MessageToDict

from coalitionkit_contracts import (
    SchemaValidationError,
    SignatureError,
    sign_consent,
    sign_owner_proof,
    validate_envelope,
    verify_consent,
    verify_envelope,
)
from coalitionkit_edges.a2a import (
    ENVELOPE_MEDIA_TYPE,
    EXTENSION_URI,
    CardError,
    CardRegistry,
    EdgeCallError,
    MemberClient,
    ReceivedError,
    fetch_card,
    verify_card,
)
from coalitionkit_edges.a2a.wire import envelope_part

if TYPE_CHECKING:
    from conftest import MakeCard, Rig, Signed

FULL_HEADERS = {"A2A-Version": "1.0", "A2A-Extensions": EXTENSION_URI}


def rpc_body(envelope: dict[str, Any], task_id: str = "") -> dict[str, Any]:
    message = Message(
        message_id=str(uuid.uuid4()),
        context_id=str(envelope["coalition_id"]),
        task_id=task_id,
        role=Role.ROLE_USER,
        parts=[envelope_part(envelope)],
    )
    params = MessageToDict(SendMessageRequest(message=message))
    return {"jsonrpc": "2.0", "id": "1", "method": "SendMessage", "params": params}


async def test_c01_host_card_declares_the_extension_and_verifies(rig: Rig) -> None:
    response = await rig.http.get(f"{rig.server.base_url}/.well-known/agent-card.json")
    raw = response.json()
    assert raw["supportedInterfaces"][0]["protocolBinding"] == "JSONRPC"
    assert raw["supportedInterfaces"][0]["protocolVersion"] == "1.0"
    extension = raw["capabilities"]["extensions"][0]
    assert extension["uri"] == EXTENSION_URI
    assert not extension.get("required", False)
    assert raw["signatures"]
    card = rig.client.host_card
    verify_card(card, lambda kid: _pinned(rig, kid))


def _pinned(rig: Rig, kid: str) -> Any:
    from coalitionkit_edges.a2a import CardKey

    return CardKey(kid, rig.signer.private_key.public_key()) if kid == rig.signer.kid else None


async def test_c01_member_card_declares_the_extension_and_verifies(make_card: MakeCard) -> None:
    card = make_card()
    assert card.capabilities.extensions[0].uri == EXTENSION_URI
    assert not card.capabilities.extensions[0].required
    CardRegistry(COALITION_ID).admit("https://agents.example.org/p2/card.json", card)


async def test_c02_join_with_owner_key_and_proof_is_acknowledged(rig: Rig, signed: Signed) -> None:
    member = rig.member
    jwk = member.owner_jwk()
    url = member.card_url
    proof = sign_owner_proof(COALITION_ID, "p2", url, jwk, member.owner_key)
    join = signed(
        "coalition.join",
        payload={
            "card_url": url,
            "owner_key": jwk,
            "owner_proof": proof,
            "roles_requested": ["member"],
            "surfaces": ["web"],
            "vault": "local",
        },
    )
    ack = await rig.client.send(join)
    assert ack.accepted is not None
    assert ack.accepted["seq"] == 1 and ack.accepted["type"] == "coalition.join"
    assert ack.receipt["type"] == "coalition.receipt"
    assert ack.receipt["sender"] == rig.signer.card_url
    # charter acceptance: an owner-signed decision about the charter is acknowledged too
    decision = {
        "subject": {"kind": "charter", "id": COALITION_ID, "revision": 2},
        "choice": "accept",
        "consent": True,
        "decided_at": "2026-10-29T10:15:00Z",
    }
    decision["consent_sig"] = sign_consent(
        COALITION_ID, decision, member.owner_key, member.owner_kid, participant="p2"
    )
    second = await rig.client.send(signed("coalition.decide", payload=decision))
    assert second.accepted is not None
    assert second.accepted["seq"] == 2
    assert second.accepted["prev_hash"] != ack.accepted["prev_hash"]


async def test_c03_sent_envelopes_validate_and_consent_checks_the_owner_key(
    rig: Rig, signed: Signed
) -> None:
    member = rig.member
    decision: dict[str, Any] = {
        "subject": {"kind": "plan", "id": "01M4XRC2A00000000000000004", "revision": 1},
        "choice": "01M4XRC2A00000000000000004",
        "consent": True,
        "decided_at": "2026-10-29T10:15:00Z",
    }
    decision["consent_sig"] = sign_consent(
        COALITION_ID, decision, member.owner_key, member.owner_kid, participant="p2"
    )
    await rig.client.send(signed("coalition.decide", payload=decision))
    await rig.client.send(signed("coalition.offer"))
    assert len(rig.host.accepted) == 2
    for received, _ in rig.host.calls:
        validate_envelope(received)
        verify_envelope(received, member.key.public_key(), expected_kid=member.kid)
    body = rig.host.calls[0][0]["payload"]
    verify_consent(
        COALITION_ID,
        body,
        member.owner_key.public_key(),
        expected_kid=member.owner_kid,
        participant="p2",
    )
    with pytest.raises(SignatureError):
        verify_consent(COALITION_ID, body, member.key.public_key(), participant="p2")


async def test_c04_never_addresses_anyone_outside_the_scope_it_was_given(
    rig: Rig, signed: Signed
) -> None:
    scope = {"audience": "participants", "participants": ["p2", "p9"]}
    envelope = signed(scope=scope)
    with pytest.raises(EdgeCallError, match="p9"):
        await rig.client.send(envelope, addressable=frozenset({"p2", "p3"}))
    assert rig.host.calls == []
    ack = await rig.client.send(envelope, addressable=frozenset({"p2", "p9"}))
    assert ack.accepted is not None
    assert ack.accepted["scope"] == scope


async def test_c05_sends_no_field_a_payload_schema_does_not_define(
    rig: Rig, signed: Signed
) -> None:
    envelope = signed()
    envelope["payload"] = {**envelope["payload"], "reason": "because"}
    with pytest.raises(SchemaValidationError):
        await rig.client.send(envelope)
    assert rig.host.calls == []
    # past the client's own check the host still refuses it
    with pytest.raises(ReceivedError) as exc:
        await rig.client.send(envelope, validate=False)
    assert exc.value.code == "schema_invalid"
    assert rig.host.accepted == []


async def test_c14_sender_differing_from_the_token_card_is_refused(
    rig: Rig, signed: Signed
) -> None:
    forged = signed(sender="https://agents.example.org/other/card.json")
    with pytest.raises(ReceivedError) as exc:
        await rig.client.send(forged)
    assert exc.value.code == "sender_mismatch"
    assert exc.value.ref == forged["event_id"]
    assert rig.host.accepted == []
    verify_envelope(exc.value.envelope, rig.signer.private_key.public_key())


async def test_call_without_a2a_version_is_refused(rig: Rig, signed: Signed) -> None:
    headers = {"Authorization": "Bearer member-token-1", "A2A-Extensions": EXTENSION_URI}
    async with httpx.AsyncClient() as bare:  # the shared client defaults A2A-Version
        response = await bare.post(rig.rpc_url, json=rpc_body(signed()), headers=headers)
    assert "error" in response.json()
    assert "version" in response.json()["error"]["message"].lower()
    assert rig.host.calls == []


async def test_call_without_the_extension_header_is_extension_not_activated(
    rig: Rig, signed: Signed
) -> None:
    headers = {"Authorization": "Bearer member-token-1", "A2A-Version": "1.0"}
    with pytest.raises(ReceivedError) as exc:
        await rig.client.send(signed(), headers=headers)
    assert exc.value.code == "extension_not_activated"
    assert rig.host.calls == [], "Coalition data must not be read without the extension"


async def test_x_a2a_extensions_does_not_activate_the_extension(rig: Rig, signed: Signed) -> None:
    headers = {
        "Authorization": "Bearer member-token-1",
        "A2A-Version": "1.0",
        "X-A2A-Extensions": EXTENSION_URI,
    }
    with pytest.raises(ReceivedError) as exc:
        await rig.client.send(signed(), headers=headers)
    assert exc.value.code == "extension_not_activated"


async def test_call_without_a_known_bearer_token_is_unauthenticated(
    rig: Rig, signed: Signed
) -> None:
    for authorization in ({}, {"Authorization": "Bearer nope"}, {"Authorization": "Basic abc"}):
        response = await rig.http.post(
            rig.rpc_url, json=rpc_body(signed()), headers={**FULL_HEADERS, **authorization}
        )
        assert response.status_code == 401
    assert rig.host.calls == []


async def test_each_exchange_is_a_new_server_assigned_task_in_the_same_context(
    rig: Rig, signed: Signed
) -> None:
    first = await rig.client.send(signed())
    second = await rig.client.send(signed())
    assert first.context_id == second.context_id == COALITION_ID
    assert first.task_id != second.task_id
    assert uuid.UUID(first.task_id)  # assigned by the server, not by the member
    # a final task takes no more messages: the member cannot reuse it
    headers = {**FULL_HEADERS, "Authorization": "Bearer member-token-1"}
    before = len(rig.host.calls)
    response = await rig.http.post(
        rig.rpc_url, json=rpc_body(signed(), task_id=first.task_id), headers=headers
    )
    assert "error" in response.json()
    assert len(rig.host.calls) == before


async def test_context_id_must_equal_the_coalition_id(rig: Rig, signed: Signed) -> None:
    envelope = signed()
    body = rpc_body(envelope)
    body["params"]["message"]["contextId"] = "01M4XRC2A00000000000000099"
    headers = {**FULL_HEADERS, "Authorization": "Bearer member-token-1"}
    response = await rig.http.post(rig.rpc_url, json=body, headers=headers)
    task = response.json()["result"]["task"]
    assert task["status"]["state"] == "TASK_STATE_REJECTED"
    assert rig.host.calls == []


async def test_message_with_two_envelope_parts_is_refused(rig: Rig, signed: Signed) -> None:
    body = rpc_body(signed())
    part = MessageToDict(Part(data=envelope_part(signed()).data, media_type=ENVELOPE_MEDIA_TYPE))
    body["params"]["message"]["parts"].append(part)
    headers = {**FULL_HEADERS, "Authorization": "Bearer member-token-1"}
    response = await rig.http.post(rig.rpc_url, json=body, headers=headers)
    assert response.json()["result"]["task"]["status"]["state"] == "TASK_STATE_REJECTED"
    assert rig.host.calls == []


async def test_host_card_tampered_in_transit_fails_verification(rig: Rig) -> None:
    card = AgentCard()
    card.CopyFrom(rig.client.host_card)
    card.name = "Another host"
    with pytest.raises(CardError) as exc:
        verify_card(card, lambda kid: _pinned(rig, kid))
    assert exc.value.reason == "bad_signature"


async def test_client_refuses_a_host_card_signed_by_an_unpinned_key(rig: Rig) -> None:
    other = Ed25519PrivateKey.generate().public_key()
    with pytest.raises(CardError) as exc:
        await MemberClient.connect(
            rig.http, rig.signer.card_url, "member-token-1", other, rig.signer.kid
        )
    assert exc.value.reason == "bad_signature"


async def test_fetch_card_runs_the_verifier(rig: Rig) -> None:
    seen: list[AgentCard] = []
    card = await fetch_card(rig.http, rig.signer.card_url, seen.append)
    assert seen == [card]


async def test_receipt_tampering_is_caught_by_the_client(rig: Rig, signed: Signed) -> None:
    ack = await rig.client.send(signed())
    assert ack.accepted is not None
    forged = {**ack.accepted, "seq": ack.accepted["seq"] + 5}
    from coalitionkit_contracts import LogIntegrityError, verify_receipt

    with pytest.raises(LogIntegrityError):
        verify_receipt(ack.receipt, rig.signer.private_key.public_key(), accepted=forged)
