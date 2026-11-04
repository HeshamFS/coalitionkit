# SPDX-License-Identifier: Apache-2.0
"""Public questions: a pack question every seat answers in the open, such as the city it is in.

The brief asks it beside the agent's own questions. Once a seat has answered (or, for an agent
brought over MCP, written the vault key ``public:<id>``), the host publishes the answer once as
an ``observe`` from that seat with ``source: "chat"`` and the content ``"<label>: <answer>"``.
A question marked ``search`` adds the answer to that seat's web search words on place needs.
Answers are public by design, so web search does not treat them as private.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..adapter import Document
from .needs import tidy
from .seats import people, read_state

if TYPE_CHECKING:
    from coalitionkit_packs import PublicQuestion

    from .engine import RoomEngine

BRIEF_KEY = "_room_brief"
VAULT_PREFIX = "public:"
QUESTION_PREFIX = "pub-"
ANSWER_MAX = 60
WHY = "Everyone in the room sees this answer."


def declared(engine: RoomEngine, coalition: str) -> list[PublicQuestion]:
    pack = engine.server.bound_pack(coalition)
    return list(getattr(pack.manifest, "public", None) or []) if pack is not None else []


def questions(engine: RoomEngine, coalition: str, ref: str) -> list[Document]:
    """One brief question per declared public question, rendered like the agent's own."""
    from .brief import COMPONENT, composed

    out: list[Document] = []
    for item in declared(engine, coalition):
        q = item.question
        question: Document = {
            "id": QUESTION_PREFIX + item.id,
            "ask": q.text,
            "why": item.why or q.why or WHY,
            "kind": q.kind,
            "component": COMPONENT[q.kind],
            "options": [{"id": f"o{i + 1}", "label": o} for i, o in enumerate(q.options)],
            "low": 0,
            "high": 0,
            "step": 1,
            "unit": "",
            "status": "open",
            "answer": None,
            "public": item.id,
        }
        question["messages"] = composed(engine, question, ref)
        out.append(question)
    return out


def clean(text: str) -> str:
    """One short line: no new lines, at most sixty characters."""
    return tidy(" ".join(str(text).split()), ANSWER_MAX).rstrip(" .")


def answer_of(engine: RoomEngine, coalition: str, who: str, item: PublicQuestion) -> str | None:
    """This seat's answer to the question, from its brief or the vault key; None when not given."""
    vault = engine.vault(coalition, who)
    for q in vault.get(BRIEF_KEY, {}).get("questions", []):
        if q.get("public") != item.id or q["status"] != "answered":
            continue
        answer: Any = q["answer"]
        labels = {o["id"]: o["label"] for o in q["options"]}
        return clean(labels.get(answer, answer)) or None
    given: Any = vault.get(VAULT_PREFIX + item.id)
    if isinstance(given, str) and given.strip():
        if item.question.kind == "choice":
            known = {o.casefold(): o for o in item.question.options}
            return known.get(given.strip().casefold())
        return clean(given) or None
    return None


def published(doc: Document) -> dict[str, dict[str, str]]:
    """``{seat: {question id: answer}}`` for every answer the room has seen."""
    return doc.get("public", {})


async def advance(engine: RoomEngine, coalition: str) -> None:
    """Publish each answer not published yet, once, from the seat that gave it."""
    items = declared(engine, coalition)
    if not items:
        return
    state = await read_state(engine, coalition)
    doc = engine.read(coalition)
    if not doc.get("begun"):
        return
    seen = published(doc)
    for who in people(state, doc):
        for item in items:
            if item.id in seen.get(who, {}):
                continue
            answer = answer_of(engine, coalition, who, item)
            if answer is None:
                continue
            await publish(engine, coalition, who, item, answer)


async def publish(
    engine: RoomEngine, coalition: str, who: str, item: PublicQuestion, answer: str
) -> None:
    try:
        sent = await engine.submit(
            coalition,
            who,
            "observe",
            {"source": "chat", "content": f"{item.label}: {answer}"},
            {"audience": "coalition"},
        )
    except Exception:  # a seat the host holds no keys for still has its answer used for search
        sent = None

    def put(d: Document) -> None:
        d.setdefault("public", {}).setdefault(who, {})[item.id] = answer

    engine.update(coalition, put)
    if sent is not None:
        engine.start_activity(
            coalition, "saying", f"{item.label}: {answer}", seat=who, state="done",
            event=str(sent["event_id"]),
        )  # fmt: skip


def search_words(engine: RoomEngine, coalition: str, who: str) -> str | None:
    """The published answers this seat's searches carry (questions marked ``search``)."""
    marked = [q.id for q in declared(engine, coalition) if q.search]
    if not marked:
        return None
    mine = published(engine.read(coalition)).get(who, {})
    words = [mine[i] for i in marked if mine.get(i)]
    return ", ".join(words) or None


def search_places(engine: RoomEngine, coalition: str) -> dict[str, str]:
    """``{seat: search words}`` for every seat with a published search answer."""
    if not any(q.search for q in declared(engine, coalition)):
        return {}
    out: dict[str, str] = {}
    for who in published(engine.read(coalition)):
        words = search_words(engine, coalition, who)
        if words:
            out[who] = words
    return out


def facts(engine: RoomEngine, coalition: str, labels: dict[str, str]) -> list[Document]:
    """What makers may see: each person's published answers, by their seat label."""
    out: list[Document] = []
    for who, answers in published(engine.read(coalition)).items():
        out.append({"who": labels.get(who, who), **answers})
    return out


def is_public(question: Document) -> bool:
    return bool(question.get("public"))
