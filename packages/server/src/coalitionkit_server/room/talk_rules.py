# SPDX-License-Identifier: Apache-2.0
"""Fixed rules of the talk: what a seat may say, and what it must never say.

Code, not the model, decides whether a line goes out. A line is checked against its closed
shape (who it is for, its intent, its length, the line it answers) and against the speaker's own
private values: the answers that person gave their agent. A value the person asked their agent
to say themselves is theirs to share, so a whisper lifts the block for the words it holds.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel

from coalitionkit_contracts.payloads import SAY_MAX_CHARS

from ..adapter import Document
from .needs import tidy

Intent = Literal["ask", "answer", "trade", "caveat", "agree", "disagree"]
INTENTS: frozenset[str] = frozenset({"ask", "answer", "trade", "caveat", "agree", "disagree"})
MIN_WORD = 4  # a shorter choice ("yes", "no") is too common a word to hold back
LEAD = re.compile(
    r"^(please\s+)?(tell|let)\s+(them|everyone|everybody|the others|the room|the group)"
    r"(\s+know)?(\s+that)?[:,]?\s*",
    re.I,
)


class TalkReply(BaseModel):
    """One turn: speak or pass, and the needs whose own offer the agent would change."""

    speak: bool
    to: str
    intent: Intent
    text: str
    re: int
    revise: list[str]


class Line(BaseModel):
    to: str
    intent: Intent
    text: str
    re: str | None


def checked(reply: TalkReply | None, others: set[str], thread: list[Document]) -> Line | None:
    """The line as the room may get it, or None for a pass."""
    if reply is None or not reply.speak:
        return None
    text = tidy(reply.text, SAY_MAX_CHARS)
    if not text or reply.intent not in INTENTS:
        return None
    to = reply.to if reply.to in others else "room"
    cited = thread[reply.re - 1]["id"] if 1 <= reply.re <= len(thread) else None
    return Line(to=to, intent=reply.intent, text=text, re=cited)


def whispered(text: str) -> str:
    """What the person asked their agent to say, without the "tell them" in front."""
    body = LEAD.sub("", text.strip()).strip()
    return tidy(body[:1].upper() + body[1:] if body else text.strip(), SAY_MAX_CHARS)


def private_values(told: list[Document], public: str) -> list[str]:
    """The person's own answers, as words a line must not hold. Words the room already shows
    (a need's title, the goal, a time everyone shares) are not private."""
    shown = {w for w in re.findall(r"\w+", public.lower()) if len(w) >= MIN_WORD}
    found: list[str] = []
    for item in told:
        answer: object = item["answer"]
        listed: list[object] = list(answer) if isinstance(answer, list) else [answer]  # pyright: ignore[reportUnknownArgumentType]
        values = [str(a) for a in listed]
        for value in values:
            value = value.strip()
            if item["kind"] == "amount" or (
                len(value) >= MIN_WORD
                and not (value.lower() in public.lower() or public_value(value, shown))
            ):
                found.append(value)
    return found


def public_value(value: str, shown: set[str]) -> bool:
    """Every word of the value that carries meaning is already on the room's screen."""
    words = [w for w in re.findall(r"\w+", value.lower()) if len(w) >= MIN_WORD]
    return bool(words) and all(w in shown for w in words)


def leaked(text: str, values: list[str], allowed: str = "") -> str | None:
    """The first private value the line holds, or None. A whisper's own words are allowed."""
    said, mine = text.lower(), allowed.lower()
    for value in values:
        low = value.lower()
        if not low or low in mine:
            continue
        if re.fullmatch(r"\d+(\.\d+)?", low):
            if re.search(rf"(?<![\d.]){re.escape(low)}(?![\d.])", said):
                return value
        elif re.search(rf"(?<!\w){re.escape(low)}(?!\w)", said):
            return value
    return None
