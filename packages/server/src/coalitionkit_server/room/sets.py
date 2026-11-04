# SPDX-License-Identifier: Apache-2.0
"""Compared sets: the private sets a bound pack declares, compared without showing any list.

A pack's ``compare`` entries each name a set and one question. Every seated person's brief asks
that question beside the agent's own; the answer stays in that seat's vault. A seat whose own
agent acts over MCP may instead write its values to the vault key ``compare:<id>``. After the
offers, for each set, the host asks every seat's vault whether it holds values (``query`` /
``answer``), then the first seat that does meets each of the others in a blinded intersection
over the strings ``"<id>:<value>"`` (``match`` rounds), carrying only the running overlap. One
public ``observe`` publishes the shared values, or in count mode only how many there are.
Nothing else about anyone's values leaves the vault.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from coalitionkit_runtime import Acknowledgement
from coalitionkit_runtime.lifecycle import State
from coalitionkit_vault._group import SodiumUnavailable
from coalitionkit_vault.psi import Context, Requester, Responder

from ..adapter import Document
from .seats import people, read_state

if TYPE_CHECKING:
    from coalitionkit_packs import CompareSet

    from .engine import RoomEngine

BRIEF_KEY = "_room_brief"
VAULT_PREFIX = "compare:"
QUESTION_PREFIX = "set-"
TEXT_VALUES = 20
VALUE_MAX = 60
WHY = "Only what everyone shares is shown; the rest of your answer stays with your agent."
Activity = Callable[[Document], Awaitable[None]]


def hook(engine: RoomEngine, coalition: str) -> Activity | None:
    """Where each PSI round is reported (contract: tool ``psi:compare``). Wired at merge time."""
    return None


def declared(engine: RoomEngine, coalition: str) -> list[CompareSet]:
    pack = engine.server.bound_pack(coalition)
    return list(pack.manifest.compare or []) if pack is not None else []


# --- the question ------------------------------------------------------------------------------
def questions(
    engine: RoomEngine, coalition: str, slots: list[Document], ref: str
) -> list[Document]:
    """One brief question per declared set, rendered like the agent's own questions."""
    from .brief import COMPONENT, composed

    out: list[Document] = []
    for item in declared(engine, coalition):
        q = item.question
        if q.kind == "slots" and not slots:
            continue
        question: Document = {
            "id": QUESTION_PREFIX + item.id,
            "ask": q.text,
            "why": q.why or WHY,
            "kind": q.kind,
            "component": COMPONENT[q.kind],
            "options": [],
            "low": 0,
            "high": 0,
            "step": 1,
            "unit": "",
            "status": "open",
            "answer": None,
            "set": item.id,
            "multiple": q.kind == "choice",
        }
        if q.kind == "choice":
            question["options"] = [{"id": f"o{i + 1}", "label": o} for i, o in enumerate(q.options)]
        elif q.kind == "slots":
            question["options"] = [{"id": s["id"], "label": s["label"]} for s in slots]
        question["messages"] = composed(engine, question, ref)
        out.append(question)
    return out


def normal(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()[:VALUE_MAX]


def from_text(text: str) -> list[str]:
    found = [normal(v) for v in re.split(r"[,\n;]", text)]
    return list(dict.fromkeys(v for v in found if v))[:TEXT_VALUES]


def canonical(item: CompareSet, raw: list[str], slots: list[Document]) -> list[str]:
    """Values in the set's closed shape: an option's own label, a slot's label, or plain text."""
    if item.question.kind == "text":
        return sorted(from_text("\n".join(raw)))
    if item.question.kind == "choice":
        known = {normal(o): o for o in item.question.options}
    else:
        known = {normal(s["label"]): s["label"] for s in slots}
        known.update({normal(s["id"]): s["label"] for s in slots})
    return sorted({known[normal(v)] for v in raw if normal(v) in known})


def values_of(engine: RoomEngine, coalition: str, who: str, item: CompareSet) -> list[str]:
    """This seat's own values for the set (empty when it gave none). Never leaves the host."""
    vault = engine.vault(coalition, who)
    slots: list[Document] = engine.read(coalition)["slots"]
    record: Document = vault.get(BRIEF_KEY, {})
    for q in record.get("questions", []):
        if q.get("set") != item.id or q["status"] != "answered":
            continue
        labels = {o["id"]: o["label"] for o in q["options"]}
        answer = q["answer"]
        if q["kind"] == "text":
            return canonical(item, [str(answer)], slots)
        return canonical(item, [labels.get(a, a) for a in answer], slots)
    given: Any = vault.get(VAULT_PREFIX + item.id)
    if isinstance(given, str):
        given = [given]
    if isinstance(given, list):
        raw = [str(v) for v in given if isinstance(v, str | int)]  # pyright: ignore[reportUnknownVariableType]
        return canonical(item, raw, slots)
    return []


# --- the comparison ----------------------------------------------------------------------------
async def advance(engine: RoomEngine, coalition: str, state: State, task: str) -> None:
    """Compare every declared set that is not done yet, one after another."""
    for item in declared(engine, coalition):
        done = engine.read(coalition).get("sets", {}).get(item.id, {}).get("state") == "done"
        if not done:
            await compare_one(engine, coalition, state, task, item)


def put(engine: RoomEngine, coalition: str, set_id: str, **fields: Any) -> None:
    def change(d: Document) -> None:
        sets = d.setdefault("sets", {})
        sets[set_id] = {**sets.get(set_id, {}), **fields}

    engine.update(coalition, change)


async def compare_one(
    engine: RoomEngine, coalition: str, state: State, task: str, item: CompareSet
) -> None:
    from . import compare

    doc = engine.read(coalition)
    seated = [p for p in people(state, doc) if engine.is_hosted(coalition, p)]
    need = item.min_seats or len(people(state, doc))
    base = {"label": item.label, "mode": item.mode, "task_id": task}
    put(engine, coalition, item.id, state="asking", took_part=[], compared=0, **base)
    engine.note(coalition, "comparing", f"Asking each seat whether it holds {item.label}")
    started = time.monotonic()
    sink = hook(engine, coalition)
    args = f"{item.label}: {len(seated)} seats, {item.mode}"
    try:
        took = await ask_everyone(engine, coalition, seated, task, item)
        if len(took) < max(2, need):
            close(engine, coalition, item, took, None)
            return
        put(engine, coalition, item.id, state="crossing", took_part=took, compared=len(took))
        if sink is not None:
            await sink(activity(args, "", "started", 0, []))
        common = await cross(engine, coalition, took, task, item)
        body: Document = {"common": 1, "set": item.id, "compared": len(took)}
        if item.mode == "overlap":
            body["values"] = common
        else:
            body["count"] = len(common)
        sent = await compare.send(
            engine,
            coalition,
            took[0],
            "observe",
            {"source": "document", "content": json.dumps(body)},
            {"audience": "coalition"},
        )
        event = str(sent["event_id"])
        close(engine, coalition, item, took, common, event)
        if sink is not None:
            ms = int((time.monotonic() - started) * 1000)
            said = f"{len(common)} in common" if item.mode == "count" else ", ".join(common)
            await sink(activity(args, said or "nothing in common", "done", ms, [event]))
    except compare.Stopped:
        close(engine, coalition, item, [], None)
        if sink is not None:
            await sink(activity(args, "held by the Steward", "failed", 0, []))
    except SodiumUnavailable:
        engine.note(coalition, "comparing", compare.NO_PSI)
        close(engine, coalition, item, [], None)


def activity(args: str, result: str, status: str, ms: int, refs: list[str]) -> Document:
    """One line for the activity recorder: names and counts only, never a seat's values."""
    return {
        "seat": "host",
        "agent": "hosted",
        "tool": "psi:compare",
        "args": args,
        "result": result,
        "status": status,
        "ms": ms,
        "refs": refs,
    }


async def ask_everyone(
    engine: RoomEngine, coalition: str, seated: list[str], task: str, item: CompareSet
) -> list[str]:
    """Each seat's vault says only whether it holds values for the set; keep those that do."""
    from coalitionkit_contracts.payloads import QueryPayload
    from coalitionkit_vault.store import Facts, Vault

    from . import compare

    host = engine.server.hosts[coalition]
    took: list[str] = []
    for n, who in enumerate(seated, start=1):
        mine = values_of(engine, coalition, who, item)
        query: Document = {
            "query_id": f"q-{item.id}-{n}",
            "kind": "feasible",
            "subject": item.id,
            "deadline_ms": compare.QUERY_MS,
            "task_id": task,
        }
        state = await read_state(engine, coalition)
        if query["query_id"] not in state.queries:
            sent = await engine.thread(host.host_emit, "query", query, compare.only(who))
            if not isinstance(sent, Acknowledgement):
                raise RuntimeError("query refused: " + str(sent["payload"]["code"]))
            state = await read_state(engine, coalition)
        if not state.queries[query["query_id"]]["answered"]:
            vault = Vault(who)
            vault.put(item.id, Facts(sets={item.id: frozenset(mine)} if mine else {}))
            answer = vault.answer(QueryPayload.model_validate(query)).to_wire()
            await compare.send(engine, coalition, who, "answer", answer, compare.only(who))
        engine.note(coalition, "comparing", f"Answered whether it holds {item.label}", seat=who)
        if mine:
            took.append(who)
    return took


async def cross(
    engine: RoomEngine, coalition: str, took: list[str], task: str, item: CompareSet
) -> list[str]:
    """The first seat against each of the others in turn; only the running overlap goes on."""
    first = took[0]
    running = values_of(engine, coalition, first, item)
    for index, other in enumerate(took[1:], start=1):
        state = await read_state(engine, coalition)
        prefix = f"{item.id}-m{index}x"
        attempt = sum(1 for m in state.matches if m.startswith(prefix))
        theirs = values_of(engine, coalition, other, item)
        running = await exchange(
            engine, coalition, task, f"{prefix}{attempt}", (first, running), (other, theirs), item
        )
        label = f"Crossed {item.label} through blinded rounds"
        engine.note(coalition, "comparing", label, seat=other)
    return running


async def exchange(
    engine: RoomEngine,
    coalition: str,
    task: str,
    match_id: str,
    asking: tuple[str, list[str]],
    answering: tuple[str, list[str]],
    item: CompareSet,
) -> list[str]:
    """One blinded intersection over ``"<id>:<value>"``: setup, request, response."""
    from . import compare

    (asker, mine), (answerer, theirs) = asking, answering
    registry = engine.server.registry
    a_key = registry.hosted_for(coalition, asker).agent_key
    b_key = registry.hosted_for(coalition, answerer).agent_key
    context = Context(coalition, match_id, asker, answerer, "overlap", task)
    prefix = item.id + ":"
    requester = Requester(context, [prefix + v for v in mine], a_key, b_key.public_key())
    responder = Responder(context, [prefix + v for v in theirs], b_key, a_key.public_key())
    pair = compare.only(asker, answerer)
    setup = responder.setup()
    await compare.send(engine, coalition, answerer, "match", setup.to_wire(), pair)
    request = requester.request(setup)
    await compare.send(engine, coalition, asker, "match", request.to_wire(), pair)
    response = responder.respond(request)
    await compare.send(engine, coalition, answerer, "match", response.to_wire(), pair)
    found = requester.finish(response)
    assert isinstance(found, list)
    return sorted(v[len(prefix) :] for v in found)


def close(
    engine: RoomEngine,
    coalition: str,
    item: CompareSet,
    took: list[str],
    common: list[str] | None,
    event: str | None = None,
) -> None:
    """Done. In count mode only the number is kept; the values never reach the room document."""
    published = common is not None
    label = f"Compared {item.label}" if published else f"Too few seats gave {item.label}"
    engine.note(coalition, "comparing", label)
    put(
        engine,
        coalition,
        item.id,
        state="done",
        took_part=took,
        compared=len(took),
        published=published,
        values=common if common is not None and item.mode == "overlap" else None,
        count=len(common) if common is not None else None,
        event=event,
    )


# --- what the room sees ------------------------------------------------------------------------
def public_sets(doc: Document) -> list[Document]:
    """The sets as the whole room may see them: label, mode and what was published."""
    out: list[Document] = []
    for set_id, s in doc.get("sets", {}).items():
        out.append(
            {
                "id": set_id,
                "label": s["label"],
                "mode": s["mode"],
                "state": s["state"],
                "values": s.get("values"),
                "count": s.get("count"),
                "compared": s.get("compared", 0),
                "event": s.get("event"),
            }
        )
    return out


def mine(engine: RoomEngine, coalition: str, viewer: str, doc: Document) -> Document:
    """For this viewer only: how many of their own values stayed private, per compared set."""
    out: Document = {}
    for item in declared(engine, coalition):
        s = doc.get("sets", {}).get(item.id)
        if not s or s["state"] != "done" or not s.get("published"):
            continue
        if viewer not in s["took_part"]:
            continue
        own = values_of(engine, coalition, viewer, item)
        out[item.id] = len(own) - int(s["count"] or 0)
    return out


def facts(engine: RoomEngine, coalition: str, doc: Document) -> Document:
    """Published sets for plans and makers: the shared values (or the count) and the options."""
    out: Document = {}
    for item in declared(engine, coalition):
        s = doc.get("sets", {}).get(item.id)
        if not s or not s.get("published"):
            continue
        entry: Document = {"label": item.label, "mode": item.mode}
        if item.mode == "overlap":
            entry["values"] = list(s["values"])
            entry["choose_only_from_these"] = True
        else:
            entry["count"] = s["count"]
        if item.question.kind == "choice":
            entry["options"] = list(item.question.options)
        out[item.id] = entry
    return out


def strays(text: str, shared: Document) -> list[str]:
    """Options a made thing names although not everyone shares them."""
    low = text.casefold()
    found: list[str] = []
    for entry in shared.values():
        if entry.get("values") is None:
            continue
        keep = {v.casefold() for v in entry["values"]}
        for option in entry.get("options", []):
            word = option.casefold()
            if word not in keep and re.search(rf"(?<!\w){re.escape(word)}(?!\w)", low):
                found.append(option)
    return found
