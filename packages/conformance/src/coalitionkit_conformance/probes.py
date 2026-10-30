# SPDX-License-Identifier: Apache-2.0
"""Active A2A probes. Missing coverage is never promoted to a passing test."""

import asyncio
from collections.abc import Awaitable, Callable
from copy import deepcopy

from coalitionkit_contracts import (
    LogIntegrityError,
    check_receipts,
    sign_envelope,
    validate_envelope,
    verify_chain,
    verify_envelope,
    verify_receipt,
)
from coalitionkit_edges.a2a.client import Ack, ReceivedError
from coalitionkit_edges.a2a.identity import CardKey

from .operator import OperatorUnavailable
from .report import Document
from .wire import Participant


async def refused(person: Participant, event: Document, code: str) -> Document:
    try:
        await person.client.send(event, validate=False)
    except ReceivedError as exc:
        validate_envelope(exc.envelope)
        if exc.code != code:
            raise AssertionError(f"expected {code}, received {exc.code}") from exc
        if exc.ref != event["event_id"]:
            raise AssertionError("error references another event") from exc
        return exc.detail
    raise AssertionError(f"accepted an event requiring {code}")


async def duplicates(people: list[Participant]) -> str:
    p = people[0]
    event = p.event("observe", {"source": "device", "content": "duplicate probe"})
    first = await p.client.send(event)
    again = await p.client.send(event)
    if first.accepted != again.accepted or first.receipt != again.receipt:
        raise AssertionError("duplicate acknowledgement changed")
    changed = deepcopy(event)
    changed["payload"]["content"] = "changed"
    changed["sig"] = sign_envelope(changed, p.key, "agent")
    if await refused(p, changed, "duplicate_mismatch") != {}:
        raise AssertionError("duplicate_mismatch detail leaks information")
    if len(people) > 1:
        other = people[1]
        changed = other.event("observe", event["payload"])
        changed["event_id"] = event["event_id"]
        changed["sig"] = sign_envelope(changed, other.key, "agent")
        if await refused(other, changed, "duplicate_mismatch") != {}:
            raise AssertionError("cross-sender mismatch detail leaks information")
    # Repeat with no event visible to its sender.
    hidden = p.event("observe", {"source": "device", "content": "private"}, {"audience": "host"})
    a, b = await p.client.send(hidden), await p.client.send(hidden)
    if a.accepted is not None or b.accepted is not None or a.receipt != b.receipt:
        raise AssertionError("duplicate of a hidden event leaks or changes")
    return (
        f"observe {event['event_id']}: stable duplicate receipts; "
        f"hidden {hidden['event_id']}: receipt-only duplicate; changed bytes: duplicate_mismatch"
    )


async def binding(p: Participant) -> str:
    event = p.event("observe", {"source": "device", "content": "binding"})
    event["sender"] = "https://other.invalid/card"
    event["sig"] = sign_envelope(event, p.key, "agent")
    await refused(p, event, "sender_mismatch")
    return f"observe {event['event_id']}, changed sender: sender_mismatch"


async def payload_fields(p: Participant) -> str:
    event = p.event("observe", {"source": "device", "content": "fields", "extra": True})
    await refused(p, event, "schema_invalid")
    ack = await p.client.send(p.event("observe", {"source": "device", "content": "valid"}))
    validate_envelope(ack.receipt)
    if ack.accepted is None:
        raise AssertionError("coalition event absent from its sender's acknowledgement")
    validate_envelope(ack.accepted)
    verify_envelope(ack.accepted, p.key.public_key(), expected_kid="agent")
    return (
        f"observe {event['event_id']} with extra field: schema_invalid; "
        f"valid observe {ack.accepted['event_id']}: seq={ack.accepted['seq']}, receipt verifies"
    )


async def scope_ack(p: Participant) -> str:
    event = p.event(
        "observe", {"source": "device", "content": "hidden-marker"}, {"audience": "host"}
    )
    for _ in range(2):
        ack = await p.client.send(event)
        if ack.accepted is not None or "hidden-marker" in str(ack.receipt):
            raise AssertionError("host-only content delivered to its sender")
    event = p.event(
        "observe",
        {"source": "device", "content": "redacted-marker"},
        {"audience": "coalition", "redact": ["payload.content"]},
    )
    for _ in range(2):
        ack = await p.client.send(event)
        if ack.accepted is None or ack.accepted.get("type") != "coalition.projection":
            raise AssertionError("redacted event was not a host-signed projection")
        if "redacted-marker" in str(ack.accepted):
            raise AssertionError("projection leaks a redacted field")
    return "Original and duplicate host-only acknowledgements and redacted projections checked"


async def chain(people: list[Participant], host: CardKey) -> str:
    async def send(p: Participant) -> Ack:
        return await p.client.send(p.event("observe", {"source": "device", "content": "chain"}))

    acks = await asyncio.gather(*(send(p) for p in people for _ in range(3)))
    entries: list[Document] = []
    for ack in acks:
        if ack.accepted is None:
            raise AssertionError("coalition event missing from acknowledgement")
        entries.append(ack.accepted)
    entries.sort(key=lambda e: int(e["seq"]))
    receipts = [verify_receipt(a.receipt, host.public_key, accepted=a.accepted) for a in acks]
    verify_chain(entries, entries[0]["prev_hash"], host.public_key, first_seq=entries[0]["seq"])
    check_receipts(entries, receipts, host.public_key)
    edited = deepcopy(entries)
    edited[-1]["payload"]["content"] = "edited"
    for replay in (entries[:-1], edited):
        try:
            check_receipts(replay, receipts, host.public_key)
        except LogIntegrityError:
            continue
        raise AssertionError("kept receipts did not detect edited or truncated tail")
    return (
        f"{len(entries)} concurrent observes seq={entries[0]['seq']}..{entries[-1]['seq']}; "
        f"ids={','.join(e['event_id'] for e in entries)}; "
        "gap-free chain, verified receipts detect edited and truncated tails"
    )


async def authorization(p: Participant) -> str:
    event = p.event("dissolve", {"reason": "cancelled", "skills_written": []})
    await refused(p, event, "not_authorized")
    return f"member dissolve {event['event_id']}: not_authorized"


async def run_probe(
    result: Document, probe: Callable[[], Awaitable[str]], missing: str | None = None
) -> None:
    result.pop("evidence", None)
    try:
        evidence = await probe()
    except OperatorUnavailable as exc:
        result.update(status="not run", reason=str(exc))
    except Exception as exc:
        result.update(status="fail", reason=f"{type(exc).__name__}: {exc}")
    else:
        result["evidence"] = evidence
        result["status"] = "not run" if missing else "pass"
        if missing:
            result["reason"] = missing
        else:
            result.pop("reason", None)


async def host_probes(tests: list[Document], people: list[Participant], host: CardKey) -> None:
    by_id = {t["id"]: t for t in tests}
    probes: list[tuple[str, Callable[[], Awaitable[str]], str | None]] = [
        (
            "C-05",
            lambda: payload_fields(people[0]),
            "Member output generation cannot be exercised through a host submission endpoint",
        ),
        (
            "C-09",
            lambda: chain(people, host),
            None,
        ),
        (
            "C-11",
            lambda: scope_ack(people[0]),
            "Observer delivery and mixed replay need inbound member and replay endpoints",
        ),
        (
            "C-13",
            lambda: duplicates(people),
            None if len(people) > 1 else "Cross-sender duplicate requires a second invitation",
        ),
        ("C-14", lambda: binding(people[0]), None),
        (
            "C-20",
            lambda: authorization(people[0]),
            "Remaining authorization rows need operator-created tasks and commitments",
        ),
    ]
    for test_id, probe, missing in probes:
        if test_id in by_id:
            await run_probe(by_id[test_id], probe, missing)
