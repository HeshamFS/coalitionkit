# SPDX-License-Identifier: Apache-2.0
"""Compare: which times fit everyone, without anyone showing their list.

The host asks each person's vault one question (``query`` / ``answer``): do you hold times at
all? Those who say yes take part. The first of them then meets each of the others in a blinded
set intersection (``match`` setup, request, response through ``coalitionkit_vault.psi``), carrying
only the running overlap forward, so no one sees another's list. Only the times that fit all are
published, in one public ``observe`` from the first person's agent. A person who skipped the
times sits out; with fewer than two people there is no crossing and nothing is published.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from coalitionkit_runtime import Acknowledgement, CoalitionHost
from coalitionkit_runtime.lifecycle import State
from coalitionkit_vault.psi import Context, Requester, Responder
from coalitionkit_vault.store import Facts, Vault

from ..adapter import Document
from .brief import chosen_slots
from .seats import people, read_state

if TYPE_CHECKING:
    from .engine import RoomEngine

KEY = "_room_compare"
SUBJECT = "slots"
QUERY_MS = 120_000


class Stopped(Exception):
    """The Steward held a message of the comparison; there is nothing honest to publish."""


def only(*seats: str) -> Document:
    return {"audience": "participants", "participants": list(seats)}


def task_for(doc: Document) -> str | None:
    """The need the comparison hangs on: a schedule need if there is one, else the first."""
    needs = doc["needs"]
    pick = next((n for n in needs if n["kind"] == "schedule"), needs[0] if needs else None)
    return str(pick["id"]) if pick else None


async def send(
    engine: RoomEngine, coalition: str, who: str, kind: str, payload: Document, scope: Document
) -> Document:
    sent = await engine.submit(coalition, who, kind, payload, scope)
    if sent is None:
        raise Stopped(kind)
    return sent


def ask_vault(engine: RoomEngine, coalition: str, who: str, query: Document) -> Document:
    """The seat's own vault answers from its private times; the room sees only yes or no."""
    from coalitionkit_contracts.payloads import QueryPayload

    mine = chosen_slots(engine, coalition, who)
    vault = Vault(who)
    vault.put(SUBJECT, Facts(sets={SUBJECT: frozenset(mine)} if mine else {}))
    return vault.answer(QueryPayload.model_validate(query)).to_wire()


async def advance(engine: RoomEngine, coalition: str) -> None:
    doc = engine.read(coalition)
    if not doc["offers_done"] or (doc["compare"] and doc["compare"]["state"] == "done"):
        return
    state = await read_state(engine, coalition)
    task = task_for(doc)
    if task is None or task not in state.tasks:
        return
    if doc["compare"] is None:
        start: Document = {"state": "asking", "task_id": task, "took_part": [], "slots": None}
        engine.update(coalition, lambda d: d.__setitem__("compare", {**start, "compared": 0}))
        engine.note(coalition, "comparing", "Asking each seat whether it holds times")
        doc = engine.read(coalition)
    try:
        await run(engine, coalition, state, doc, task)
    except Stopped:
        # A held message leaves nothing honest to publish: no crossing, and the room moves on.
        finish(engine, coalition, [], None)


async def run(engine: RoomEngine, coalition: str, state: State, doc: Document, task: str) -> None:
    if doc["compare"]["state"] == "asking":
        seated = [p for p in people(state, doc) if engine.is_hosted(coalition, p)]
        took = await ask_everyone(engine, coalition, seated, task)
        if len(took) < 2:
            finish(engine, coalition, took, None)
            return
        engine.update(
            coalition,
            lambda d: d["compare"].update(state="crossing", took_part=took, compared=len(took)),
        )
        doc = engine.read(coalition)
    took = doc["compare"]["took_part"]
    slots = await cross(engine, coalition, took, task)
    content = common_content(doc, slots)
    await send(
        engine,
        coalition,
        took[0],
        "observe",
        {"source": "document", "content": content},
        {"audience": "coalition"},
    )
    finish(engine, coalition, took, slots)


async def ask_everyone(
    engine: RoomEngine, coalition: str, seated: list[str], task: str
) -> list[str]:
    """Query each seat once (this also starts planning on the task) and keep those who say yes."""
    host = engine.server.hosts[coalition]
    took: list[str] = []
    for n, who in enumerate(seated, start=1):
        query: Document = {
            "query_id": f"q-times-{n}",
            "kind": "feasible",
            "subject": SUBJECT,
            "deadline_ms": QUERY_MS,
            "task_id": task,
        }
        state = await read_state(engine, coalition)
        if query["query_id"] not in state.queries:
            sent = await _host_query(engine, host, query, who)
            if not isinstance(sent, Acknowledgement):
                raise RuntimeError("query refused: " + str(sent["payload"]["code"]))
            state = await read_state(engine, coalition)
        if not state.queries[query["query_id"]]["answered"]:
            answer = ask_vault(engine, coalition, who, query)
            await send(engine, coalition, who, "answer", answer, only(who))
            result = answer["result"]
        else:
            result = "yes" if chosen_slots(engine, coalition, who) else "no"
        engine.note(coalition, "comparing", "Answered whether it holds times", seat=who)
        if result == "yes":
            took.append(who)
    return took


async def _host_query(
    engine: RoomEngine, host: CoalitionHost, query: Document, who: str
) -> Acknowledgement | Document:
    return await engine.thread(host.host_emit, "query", query, only(who))


async def cross(engine: RoomEngine, coalition: str, took: list[str], task: str) -> list[str]:
    """First person against each of the others in turn; the overlap so far stays with them."""
    first = took[0]
    running = chosen_slots(engine, coalition, first)
    for index, other in enumerate(took[1:], start=1):
        state = await read_state(engine, coalition)
        attempt = sum(1 for m in state.matches if m.startswith(f"m{index}x"))
        running = await exchange(
            engine, coalition, task, f"m{index}x{attempt}", first, other, running
        )
        engine.note(coalition, "comparing", "Crossed times through blinded rounds", seat=other)
    return running


async def exchange(
    engine: RoomEngine,
    coalition: str,
    task: str,
    match_id: str,
    asker: str,
    answerer: str,
    mine: list[str],
) -> list[str]:
    """One blinded intersection: setup, request, response, each a signed ``match`` event."""
    registry = engine.server.registry
    a_key = registry.hosted_for(coalition, asker).agent_key
    b_key = registry.hosted_for(coalition, answerer).agent_key
    context = Context(coalition, match_id, asker, answerer, "overlap", task)
    theirs = chosen_slots(engine, coalition, answerer)
    requester = Requester(context, mine, a_key, b_key.public_key())
    responder = Responder(context, theirs, b_key, a_key.public_key())
    pair = only(asker, answerer)
    setup = responder.setup()
    await send(engine, coalition, answerer, "match", setup.to_wire(), pair)
    request = requester.request(setup)
    await send(engine, coalition, asker, "match", request.to_wire(), pair)
    response = responder.respond(request)
    await send(engine, coalition, answerer, "match", response.to_wire(), pair)
    found = requester.finish(response)
    assert isinstance(found, list)
    return found


def finish(engine: RoomEngine, coalition: str, took: list[str], slots: list[str] | None) -> None:
    """Close the comparison. Fewer than two people means no crossing and nothing is published."""
    label = "Compared times" if slots is not None else "Too few seats gave times to compare"
    engine.start_activity(coalition, "comparing", label, state="done")

    def done(d: Document) -> None:
        d["compare"].update(state="done", took_part=took, compared=len(took), slots=slots)

    engine.update(coalition, done)
    engine.wake_gardener(coalition)


def common_content(doc: Document, slots: list[str]) -> str:
    return json.dumps(
        {
            "common": 1,
            "task_id": doc["compare"]["task_id"],
            "slots": slots,
            "compared": doc["compare"]["compared"],
        }
    )
