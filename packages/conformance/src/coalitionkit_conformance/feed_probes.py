# SPDX-License-Identifier: Apache-2.0
"""Checks using authenticated public feed snapshots, never operator readbacks."""

import httpx

from coalitionkit_contracts import (
    SignatureError,
    check_receipts,
    sign_consent,
    sign_envelope,
    validate_envelope,
    validate_payload,
    verify_chain,
    verify_consent,
    verify_decision,
    verify_envelope,
    verify_receipt,
)
from coalitionkit_edges.a2a.client import Ack

from .probes import refused, scope_ack
from .report import Document
from .wire import Participant


async def charter(p: Participant, http: httpx.AsyncClient, feed: str) -> str:
    view = await p.view(http, feed)
    events = [(key, e) for key, e in view["events"].items() if e["type"] == "coalition.charter"]
    if len(events) != 1:
        raise AssertionError("fresh Coalition must deliver one charter")
    event_id, event = events[0]
    validate_payload("coalition.charter", event["payload"])
    decision = p.decision(event["payload"]["revision"])
    validate_envelope(decision)
    verify_decision(decision, p.key.public_key(), p.owner.public_key())
    try:
        verify_consent(
            p.coalition, decision["payload"], p.key.public_key(), participant=p.participant
        )
    except SignatureError:
        pass
    else:
        raise AssertionError("owner consent verified with agent key")
    ack = await p.client.send(decision)
    if ack.accepted is None:
        raise AssertionError("charter acknowledgement missing")
    verify_decision(ack.accepted, p.key.public_key(), p.owner.public_key())
    return (
        f"received charter {event_id} revision={event['payload']['revision']}; "
        f"sent decide {decision['event_id']}, accepted seq={ack.accepted['seq']}"
    )


async def consent_rejections(p: Participant) -> str:
    bad = p.decision()
    bad["payload"]["consent_sig"] = sign_consent(
        p.coalition, bad["payload"], p.key, "agent", participant=p.participant
    )
    bad["sig"] = sign_envelope(bad, p.key, "agent")
    await refused(p, bad, "bad_signature")
    stale = p.decision(2)
    await refused(p, stale, "stale_subject")
    duplicate = p.decision()
    await refused(p, duplicate, "not_authorized")
    return (
        f"decide {bad['event_id']}: bad_signature; {stale['event_id']}: stale_subject; "
        f"{duplicate['event_id']}: not_authorized"
    )


async def observer(people: list[Participant], http: httpx.AsyncClient, feed: str) -> str:
    p, observer = people[:2]
    evidence = await scope_ack(p)
    sent: list[str] = []
    for scope in (
        {"audience": "host"},
        {"audience": "self"},
        {"audience": "participants", "participants": [p.participant]},
    ):
        event = p.event("observe", {"source": "device", "content": "private-marker"}, scope)
        await p.client.send(event)
        sent.append(event["event_id"])
    event = p.event(
        "observe",
        {"source": "device", "content": "redacted-marker"},
        {"audience": "coalition", "redact": ["payload.content"]},
    )
    await p.client.send(event)
    view = await observer.view(http, feed)
    if "private-marker" in str(view) or "redacted-marker" in str(view):
        raise AssertionError("observer received content outside scope")
    entries = view["events"]
    if any(event_id in entries for event_id in sent):
        raise AssertionError("observer received a hidden envelope")
    if event["event_id"] not in entries:
        raise AssertionError("observer did not receive the redacted event")
    if "content" in entries[event["event_id"]]["payload"]:
        raise AssertionError("observer field was not removed")
    # A2A acknowledgements carry exactly the signed delivery received by the member.
    # Read a contiguous original/projection segment without the feed's lossy rendering.
    acks: list[Ack] = []
    for redacted in (False, True, False):
        scope: Document = {"audience": "coalition"}
        if redacted:
            scope["redact"] = ["payload.content"]
        ack = await p.client.send(
            p.event("observe", {"source": "device", "content": "segment"}, scope)
        )
        if ack.accepted is None:
            raise AssertionError("missing A2A delivery")
        if redacted != (ack.accepted["type"] == "coalition.projection"):
            raise AssertionError("wrong delivery form")
        if not redacted:
            verify_envelope(ack.accepted, p.key.public_key(), expected_kid="agent")
        acks.append(ack)
    from coalitionkit_edges.a2a.identity import card_keys

    host = next(iter(card_keys(p.client.host_card).values()))
    entries = [a.accepted for a in acks if a.accepted is not None]
    verify_chain(entries, entries[0]["prev_hash"], host.public_key, first_seq=entries[0]["seq"])
    receipts = [verify_receipt(a.receipt, host.public_key) for a in acks]
    check_receipts(entries, receipts, host.public_key)
    return (
        f"{evidence}; signed mixed A2A segment verifies; "
        f"hidden ids={','.join(sent)} absent for {observer.participant}; "
        f"{event['event_id']} returned with content removed"
    )
