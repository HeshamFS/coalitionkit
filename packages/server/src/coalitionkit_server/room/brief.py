# SPDX-License-Identifier: Apache-2.0
"""The brief: each seated person's agent asks up to three questions, privately.

The model picks what to ask and which closed kind each question is (choice, amount, slots or
short text); code maps the kind to one catalog component that renders with a data binding and
submits through a Button action, and composes the tree through ``compose_surface`` so every
question carries validated messages. Questions, answers and the messages live only in that
seat's vault, under ``_room_brief``. An answer is checked against its question's closed shape.
A person's brief closes when every question is answered or skipped, or after BRIEF_SECONDS.
"""

from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel

from coalitionkit_runtime.lifecycle import State
from coalitionkit_surfaces import compose_surface

from ..adapter import Document
from .model import ask
from .needs import tidy
from .seats import people

if TYPE_CHECKING:
    from .engine import RoomEngine

BRIEF_SECONDS = 300
MAX_QUESTIONS = 3
KEY = "_room_brief"
KIND = Literal["choice", "amount", "slots", "text"]
COMPONENT = {
    "choice": "ChoicePicker",
    "amount": "Slider",
    "slots": "ChoicePicker",
    "text": "TextArea",
}
TEXT_MAX = 300
ASK_MAX = 140
WHY_MAX = 160

SYSTEM = (
    "You are one person's agent in a small group room, getting ready to offer work on their "
    "behalf. Ask that person one to three short questions whose answers you need to decide "
    "which needs they can take and what it costs them. Each question has a kind: choice (pick "
    "one of two to six short options you write), amount (a whole number between low and high "
    "with a unit; for time, make it the most they would give to any one job, in hours), "
    "slots (pick any of the room's shared time slots; leave "
    "options empty) or text (a short free answer). Ask only what the goal, the needs and the "
    "slots make useful; never ask for private details that no need requires. For each question "
    "write why you ask it in one line. If the goal states an amount of money, that amount is "
    "the group's shared budget: do not ask what the budget is, and ask at most how much this "
    "person could pay themselves. Unused fields stay empty or zero."
)


class AskItem(BaseModel):
    ask: str
    why: str
    kind: KIND
    options: list[str]
    low: int
    high: int
    step: int
    unit: str


class BriefReply(BaseModel):
    questions: list[AskItem]


def fallback_items(needs: list[Document], slots: list[Document]) -> list[AskItem]:
    """Fixed questions built from the room's own needs and slots."""
    out: list[AskItem] = []
    if len(needs) >= 2:
        titles = [n["title"] for n in needs][:6]
        out.append(
            AskItem(
                ask="Which of these would you rather take on?",
                why="Your agent offers where you want to help first.",
                kind="choice",
                options=titles,
                low=0,
                high=0,
                step=0,
                unit="",
            )
        )
    if slots:
        out.append(
            AskItem(
                ask="Which of these times could you do?",
                why="Only the times everyone shares are used, and your list stays private.",
                kind="slots",
                options=[],
                low=0,
                high=0,
                step=0,
                unit="",
            )
        )
    out.append(
        AskItem(
            ask="What is the most time, in hours, you would give to any one job?",
            why="Your agent will not say any single job takes you longer than this.",
            kind="amount",
            options=[],
            low=0,
            high=20,
            step=1,
            unit="hours",
        )
    )
    if len(out) < MAX_QUESTIONS:
        out.append(
            AskItem(
                ask="Is there anything the room should know?",
                why="Your agent reads it before it offers; others do not see it.",
                kind="text",
                options=[],
                low=0,
                high=0,
                step=0,
                unit="",
            )
        )
    return out[:MAX_QUESTIONS]


def build_question(
    engine: RoomEngine, index: int, item: AskItem, slots: list[Document], ref: str
) -> Document | None:
    """A question record if the item is well formed for its kind, else None."""
    text, why = tidy(item.ask, ASK_MAX), tidy(item.why, WHY_MAX)
    if not text:
        return None
    question: Document = {
        "id": f"q{index}",
        "ask": text,
        "why": why or "Your agent asks so it can offer well.",
        "kind": item.kind,
        "component": COMPONENT[item.kind],
        "options": [],
        "low": 0,
        "high": 0,
        "step": 1,
        "unit": "",
        "status": "open",
        "answer": None,
    }
    if item.kind == "choice":
        labels = list(dict.fromkeys(t for t in (tidy(o, 60) for o in item.options) if t))[:6]
        if len(labels) < 2:
            return None
        question["options"] = [{"id": f"o{i + 1}", "label": s} for i, s in enumerate(labels)]
    elif item.kind == "slots":
        if not slots:
            return None
        question["options"] = [{"id": s["id"], "label": s["label"]} for s in slots]
    elif item.kind == "amount":
        low, high, step = item.low, item.high, max(1, item.step)
        if not 0 <= low < high <= 100000:
            return None
        question.update(low=low, high=high, step=min(step, high - low), unit=tidy(item.unit, 20))
    try:
        question["messages"] = composed(engine, question, ref)
    except ValueError:
        return None
    return question


def bound(value: int, ref: str) -> Document:
    return {"value": value, "event_ref": ref}


def tree(q: Document, ref: str) -> tuple[list[Document], Document]:
    """The components and data model of one question. Every number points at a real event."""
    kind = q["kind"]
    options = [{"id": o["id"], "label": o["label"]} for o in q["options"]]
    if kind == "choice":
        field: Document = {"component": "ChoicePicker", "display": "chips", "options": options}
        data: Any = ""
    elif kind == "slots":
        field = {
            "component": "ChoicePicker",
            "display": "chips",
            "multiple": True,
            "options": options,
        }
        data = []
    elif kind == "amount":
        low, high = q["low"], q["high"]
        field = {
            "component": "Slider",
            "min": bound(low, ref),
            "max": bound(high, ref),
            "step": bound(q["step"], ref),
        }
        if q["unit"]:
            field["unit"] = q["unit"]
        data = bound((low + high) // 2, ref)
    else:
        field = {
            "component": "TextArea",
            "label": q["ask"],
            "maxLength": bound(TEXT_MAX, ref),
        }
        data = ""
    components: list[Document] = [
        {
            "id": "root",
            "component": "Column",
            "gap": "12",
            "children": ["ask", "why", "input", "go"],
        },
        {"id": "ask", "component": "Heading", "text": q["ask"], "variant": "h3"},
        {
            "id": "why",
            "component": "Text",
            "text": q["why"],
            "variant": "caption",
            "tone": "muted",
            "provenance": "model",
        },
        {"id": "input", **field, "value": {"path": "/answer"}},
        {
            "id": "go",
            "component": "Button",
            "label": "Send",
            "variant": "primary",
            "action": {
                "name": "room.brief",
                "context": {"question_id": q["id"], "value": {"path": "/answer"}},
            },
        },
    ]
    return components, {"answer": data}


def composed(engine: RoomEngine, q: Document, ref: str) -> list[Document]:
    components, data = tree(q, ref)
    result = compose_surface(engine.catalog, f"brief-{q['id']}", components, data, {ref})
    if result.fallback:
        raise ValueError("; ".join(result.errors))
    return result.messages


def check_answer(q: Document, value: Any) -> Any:
    """The value in its closed shape, or ValueError."""
    kind = q["kind"]
    ids = {o["id"] for o in q["options"]}
    if kind == "choice":
        if isinstance(value, str) and value in ids:
            return value
    elif kind == "slots":
        if (
            isinstance(value, list)
            and value
            and all(isinstance(v, str) for v in value)  # pyright: ignore[reportUnknownVariableType]
            and len(set(value)) == len(value)  # pyright: ignore[reportUnknownArgumentType]
            and set(value) <= ids  # pyright: ignore[reportUnknownArgumentType]
        ):
            return sorted(value)  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
    elif kind == "amount":
        # The slider's default sits in the data model as {value, event_ref}; Send without moving
        # it posts that wrapper, so unwrap it before the check.
        if isinstance(value, dict) and set(value) == {"value", "event_ref"}:  # pyright: ignore[reportUnknownArgumentType]
            value = value["value"]  # pyright: ignore[reportUnknownVariableType]
        if (
            isinstance(value, int | float)
            and not isinstance(value, bool)
            and q["low"] <= value <= q["high"]
        ):
            return value
    elif isinstance(value, str):
        text = re.sub(r"\s+", " ", value).strip()
        if 0 < len(text) <= TEXT_MAX and not re.search(r"[\x00-\x08\x0b-\x1f]", value):
            return text
    raise ValueError("answer does not fit the question")


class UnknownQuestion(KeyError):
    """No such question for this seat."""


class BriefClosed(Exception):
    """The question was answered or skipped already, or the brief is over."""


def charter_ref(state: State) -> str:
    """The latest charter event: a real event every seat can see, for the numbers in a tree."""
    charters = [e for e in state.events.values() if e["type"] == "coalition.charter"]
    return str(max(charters, key=lambda e: e["seq"])["event_id"])


def questions_from(
    engine: RoomEngine, items: list[AskItem], slots: list[Document], ref: str
) -> list[Document]:
    out: list[Document] = []
    for item in items:
        if len(out) == MAX_QUESTIONS:
            break
        question = build_question(engine, len(out) + 1, item, slots, ref)
        if question is not None:
            out.append(question)
    return out


async def open_brief(engine: RoomEngine, coalition: str, who: str, state: State) -> None:
    doc = engine.read(coalition)
    needs, slots = doc["needs"], doc["slots"]
    ref = charter_ref(state)
    shown = [{"title": n["title"], "kind": n["kind"], "detail": n["detail"]} for n in needs]
    reply = await ask(
        engine,
        coalition,
        "hosted_agent",
        SYSTEM,
        {
            "goal": state.charter["goal"],
            "person": engine.name_of(coalition, who),
            "needs": shown,
            "slots": slots,
        },
        BriefReply,
        verb="asking",
        label="Your agent is choosing what to ask you",
        seat=who,
        only=who,
    )
    questions = questions_from(engine, reply.questions if reply else [], slots, ref)
    source = "model" if questions else "rules"
    if not questions:
        questions = questions_from(engine, fallback_items(needs, slots), slots, ref)
    now = engine.now()

    def opened(d: Document) -> None:
        d["briefs"][who] = {"opened": now, "closed": not questions, "source": source}

    with engine.lock:
        engine.vault_put(
            coalition, who, KEY, {"opened": now, "source": source, "questions": questions}
        )
        engine.update(coalition, opened)


def finished(record: Document) -> bool:
    return all(q["status"] != "open" for q in record["questions"])


def close(engine: RoomEngine, coalition: str, who: str) -> None:
    def shut(d: Document) -> None:
        d["briefs"][who]["closed"] = True

    engine.update(coalition, shut)


def answer(
    engine: RoomEngine,
    coalition: str,
    who: str,
    question_id: str,
    value: Any = None,
    skip: bool = False,
) -> str:
    """Save one answer (or a skip) in the seat's vault; the new status of the question."""
    with engine.lock:
        brief = engine.doc(coalition)["briefs"].get(who)
        record = engine.vault(coalition, who).get(KEY)
        if brief is None or record is None:
            raise UnknownQuestion(question_id)
        question = next((q for q in record["questions"] if q["id"] == question_id), None)
        if question is None:
            raise UnknownQuestion(question_id)
        if brief["closed"] or question["status"] != "open":
            raise BriefClosed(question_id)
        if skip:
            question["status"] = "skipped"
        else:
            question["answer"] = check_answer(question, value)  # ValueError when it does not fit
            question["status"] = "answered"
        engine.vault_put(coalition, who, KEY, record)
        if finished(record):
            close(engine, coalition, who)
        else:
            engine.bump(coalition)
        status = str(question["status"])
    engine.wake(coalition)
    return status


def close_if_due(engine: RoomEngine, coalition: str, who: str) -> None:
    """Close a brief whose questions are all done or whose time is up."""
    with engine.lock:
        brief = engine.doc(coalition)["briefs"][who]
        if brief["closed"]:
            return
        record = engine.vault(coalition, who).get(KEY)
        late = engine.now() - float(brief["opened"]) >= BRIEF_SECONDS
        if record is None or finished(record) or late:
            close(engine, coalition, who)


async def advance(engine: RoomEngine, coalition: str) -> None:
    """Open the brief of each seated person, close the ones that are over, then say when done."""
    state = await engine.thread(lambda: engine.server.hosts[coalition].state)
    doc = engine.read(coalition)
    if not doc["begun"]:
        return
    seated = people(state, doc)
    fresh = [p for p in seated if p not in doc["briefs"]]
    hosted = [p for p in fresh if engine.is_hosted(coalition, p)]
    for who in (p for p in fresh if p not in hosted):
        # An agent the person brought has no vault here to ask into.
        engine.update(coalition, lambda d, who=who: none_for(d, who, engine.now()))
    if hosted:
        engine.note(coalition, "asking", "Agents are asking their people a few questions")
        await asyncio.gather(*(open_brief(engine, coalition, who, state) for who in hosted))
    for who in seated:
        close_if_due(engine, coalition, who)
    current = engine.read(coalition)
    done = all(current["briefs"].get(p, {}).get("closed") for p in seated)
    if done != current["briefs_done"]:
        engine.update(coalition, lambda d: d.__setitem__("briefs_done", done))
        if done:
            engine.note(coalition, "planning", "The briefs are in; agents can offer")
            engine.wake_gardener(coalition)


def none_for(doc: Document, who: str, now: float) -> None:
    doc["briefs"][who] = {"opened": now, "closed": True, "source": "none"}


def given(engine: RoomEngine, coalition: str, who: str) -> list[Document]:
    """What the person told their agent, with option ids turned back into words.

    For the agent's own use: it may go to the model in a prompt and into that seat's feed, and
    nowhere else.
    """
    record: Document = engine.vault(coalition, who).get(KEY, {})
    out: list[Document] = []
    for q in record.get("questions", []):
        if q["status"] != "answered":
            continue
        labels = {o["id"]: o["label"] for o in q["options"]}
        answer = q["answer"]
        if q["kind"] == "choice":
            answer = labels.get(answer, answer)
        elif q["kind"] == "slots":
            answer = [labels.get(a, a) for a in answer]
        out.append({"ask": q["ask"], "kind": q["kind"], "unit": q["unit"], "answer": answer})
    return out


def chosen_slots(engine: RoomEngine, coalition: str, who: str) -> list[str]:
    """Slot ids this person said they can do (empty if they skipped the question)."""
    record: Document = engine.vault(coalition, who).get(KEY, {})
    found: list[str] = []
    for q in record.get("questions", []):
        if q["kind"] == "slots" and q["status"] == "answered":
            found.extend(q["answer"])
    return sorted(set(found))
