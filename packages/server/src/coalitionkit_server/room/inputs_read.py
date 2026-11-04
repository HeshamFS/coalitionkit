# SPDX-License-Identifier: Apache-2.0
"""Reading a photo or spoken words into an answer of one brief question, or a sentence to say.

The model only proposes: the reply is mapped to the question's closed kind and checked with the
same check as a typed answer (``brief.check_answer``). Nothing is saved here; the person sees the
proposal, may change it and confirms it through the existing routes. The photo goes to the
composer route as an image part and the words to the person's own agent; both calls are for the
person's own agent, so the only data in them is the person's own question and their own input.
"""

from __future__ import annotations

import asyncio
import base64
import json
import re
import time
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from coalitionkit_models import MissingKeyError
from coalitionkit_models.media import image_mime

from ..adapter import Document
from .brief import KEY, TEXT_MAX, check_answer
from .model import GUARD, complete
from .needs import tidy

if TYPE_CHECKING:
    from .engine import RoomEngine

READ_TIMEOUT_S = 40.0
DESCRIPTION_MAX = 200

ANSWER_SYSTEM = (
    "You are one person's agent in a small group room. The person answers one of your questions "
    "{how}. Give the answer in the question's kind. choice: exactly one option id in option_ids. "
    "slots: every option id that fits, in option_ids. amount: a whole number between low and "
    "high in number, and has_number true. text: a short answer in text, at most 300 characters. "
    "Write in description one plain line saying what the photo shows (leave it empty for spoken "
    "words). When the {what} does not answer the question, leave option_ids empty, has_number "
    "false and text empty: never guess an answer the person did not give."
)
SAY_SYSTEM = (
    "You are one person's agent in a small group room. The person took a photo to tell you "
    "something. Write in description one plain line saying what the photo shows, and in text "
    "one short sentence, in the first person, that the person could say about it. Leave "
    "option_ids empty and has_number false."
)


class Reading(BaseModel):
    description: str
    option_ids: list[str]
    number: int
    has_number: bool
    text: str


class Unreadable(Exception):
    """The model could not be reached or gave nothing usable."""


class NoKey(Unreadable):
    """No model key on this host."""


def open_question(engine: RoomEngine, coalition: str, who: str, question_id: str) -> Document:
    """The viewer's own open question, or LookupError (none) / PermissionError (closed)."""
    doc = engine.read(coalition)
    brief = doc["briefs"].get(who)
    record: Document = engine.vault(coalition, who).get(KEY, {})
    question = next((q for q in record.get("questions", []) if q["id"] == question_id), None)
    if brief is None or question is None:
        raise LookupError(question_id)
    if brief["closed"] or question["status"] != "open":
        raise PermissionError(question_id)
    return question


def shown_question(q: Document) -> Document:
    return {
        "question": q["ask"],
        "kind": q["kind"],
        "options": [{"id": o["id"], "label": o["label"]} for o in q["options"]],
        "low": q["low"],
        "high": q["high"],
        "unit": q["unit"],
    }


def _checked(q: Document, value: Any) -> Any:
    if value is None:
        return None
    try:
        return check_answer(q, value)
    except ValueError:
        return None


def closed_answer(q: Document, reading: Reading) -> Any:
    """The reading as a value of the question's closed kind, or None when it does not fit."""
    kind = q["kind"]
    if kind == "choice":
        value: Any = reading.option_ids[0] if len(reading.option_ids) == 1 else None
    elif kind == "slots":
        value = list(dict.fromkeys(reading.option_ids)) or None
    elif kind == "amount":
        value = reading.number if reading.has_number else None
    else:
        value = tidy(reading.text, TEXT_MAX) or None
    return _checked(q, value)


def rule_answer(q: Document, words: str) -> Any:
    """Spoken words as an answer by the words alone: labels said, or the first number in range."""
    kind, low = q["kind"], words.lower()
    named = [o["id"] for o in q["options"] if o["label"].lower() in low]
    value: Any = None
    if kind == "text":
        value = tidy(words, TEXT_MAX) or None
    elif kind == "choice" and len(named) == 1:
        value = named[0]
    elif kind == "slots" and named:
        value = named
    elif kind == "amount":
        found = [int(n) for n in re.findall(r"\d+", words)]
        value = next((n for n in found if q["low"] <= n <= q["high"]), None)
    return _checked(q, value)


def words_of(q: Document, value: Any) -> str:
    """An answer in the person's words: option labels, the number with its unit, or the text."""
    if value is None:
        return ""
    labels = {o["id"]: o["label"] for o in q["options"]}
    if q["kind"] == "choice":
        return str(labels.get(value, value))
    if q["kind"] == "slots":
        return ", ".join(str(labels.get(v, v)) for v in value)
    if q["kind"] == "amount":
        return f"{value} {q['unit']}".strip()
    return str(value)


async def read(
    engine: RoomEngine,
    coalition: str,
    who: str,
    system: str,
    data: Document,
    image: bytes | None = None,
) -> tuple[Reading, int]:
    """One schema-checked call for the viewer's own agent: (reading, ms). Raises Unreadable."""
    role = "composer" if image is not None else "hosted_agent"
    label = "Your agent is reading your photo" if image else "Your agent is reading your words"
    entry = engine.start_activity(coalition, "reading", label, seat=who, only=who, source="model")
    user: Any = json.dumps(data, ensure_ascii=False)
    if image is not None:
        url = f"data:{image_mime(image)};base64,{base64.b64encode(image).decode('ascii')}"
        user = [{"type": "text", "text": user}, {"type": "image_url", "image_url": {"url": url}}]
    messages: Any = [
        {"role": "system", "content": f"{system}\n\n{GUARD}"},
        {"role": "user", "content": user},
    ]
    started = time.monotonic()
    try:
        async with asyncio.timeout(READ_TIMEOUT_S):
            reply = await complete(engine, role, messages, coalition, who, Reading)
        parsed = reply.parsed
        if not isinstance(parsed, Reading):
            raise ValueError("reply is not a reading")
    except Exception as exc:
        if isinstance(exc, MissingKeyError) or isinstance(exc.__cause__, MissingKeyError):
            engine.end_activity(coalition, entry, state="done", ms=0, source="rules")
            raise NoKey from None
        ms = round((time.monotonic() - started) * 1000)
        why = type(exc).__name__  # never the text of the prompt or the reply
        engine.end_activity(coalition, entry, state="failed", ms=ms, source="rules", error=why)
        raise Unreadable(why) from None
    ms = round((time.monotonic() - started) * 1000)
    engine.end_activity(
        coalition,
        entry,
        state="done",
        ms=ms,
        source="model",
        cost=reply.cost_micro_usd,
        tokens=[reply.usage.prompt_tokens, reply.usage.completion_tokens],
    )
    return parsed, ms


async def answer_from_photo(
    engine: RoomEngine, coalition: str, who: str, q: Document, image: bytes
) -> tuple[Document, int]:
    system = ANSWER_SYSTEM.format(how="with a photo", what="photo")
    reading, ms = await read(engine, coalition, who, system, shown_question(q), image)
    value = closed_answer(q, reading)
    return {
        "answer": value,
        "words": words_of(q, value),
        "description": tidy(reading.description, DESCRIPTION_MAX),
    }, ms


async def say_from_photo(
    engine: RoomEngine, coalition: str, who: str, image: bytes
) -> tuple[Document, int]:
    reading, ms = await read(engine, coalition, who, SAY_SYSTEM, {"purpose": "say"}, image)
    sentence = tidy(reading.text, 300)
    return {
        "answer": sentence or None,
        "words": sentence,
        "description": tidy(reading.description, DESCRIPTION_MAX),
    }, ms


async def answer_from_words(
    engine: RoomEngine, coalition: str, who: str, q: Document, words: str
) -> tuple[Document, str]:
    """The spoken words as an answer: text as it is, else the model, else the words alone."""
    if q["kind"] == "text":
        value = rule_answer(q, words)
        return {"answer": value, "words": words_of(q, value)}, "rules"
    system = ANSWER_SYSTEM.format(how="by speaking", what="words")
    try:
        reading, _ = await read(
            engine, coalition, who, system, {**shown_question(q), "words": words}
        )
        value, source = closed_answer(q, reading), "model"
    except Unreadable:
        value, source = None, "rules"
    if value is None:
        value, source = rule_answer(q, words), "rules"
    return {"answer": value, "words": words_of(q, value)}, source
