# SPDX-License-Identifier: Apache-2.0
"""The Gardener turns the goal into needs and a few shared time slots.

When the owner accepts the charter, the ``gardener`` role splits the goal into two to six needs
(a title, a kind and a one-line detail) and up to six time slots every seat can pick from. If no
model answers, fixed rules do the same job from the draft's needs, or from the goal itself. The
titles replace the draft's needs before the Gardener loop seeds them; kind and detail stay in the
engine's document, keyed by the need's id.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel

from coalitionkit_gardener._ids import derive_ulid
from coalitionkit_runtime.lifecycle import State

from ..adapter import Document
from .model import ask

if TYPE_CHECKING:
    from .engine import RoomEngine

Kind = Literal["place", "schedule", "budget", "list", "draft"]
KINDS: tuple[str, ...] = ("place", "schedule", "budget", "list", "draft")
MAX_NEEDS = 6
MAX_SLOTS = 6
TITLE_MAX = 80
DETAIL_MAX = 160

SYSTEM = (
    "You are the Gardener of a small group room. Read the goal and split it into two to six "
    "needs the group must meet. Give each need a short title (under 70 characters, in the "
    "goal's own words), a kind that says what sort of result it needs (place, schedule, "
    "budget, list or draft) and one line of detail. Then give up to six candidate time slots "
    "as short labels, none later than the deadline, counted from the time given. Titles and "
    "details come from the goal only; do not add facts it does not hold."
)

KEYWORDS: tuple[tuple[Kind, tuple[str, ...]], ...] = (
    ("budget", ("budget", "cost", "costs", "money", "pay", "price", "fund", "afford")),
    ("schedule", ("when", "time", "schedule", "date", "day", "meet", "meeting", "agenda")),
    ("place", ("where", "place", "room", "venue", "location", "space", "site", "route")),
    ("list", ("list", "bring", "items", "supplies", "buy", "shopping", "inventory", "checklist")),
)


class NeedItem(BaseModel):
    title: str
    kind: Kind
    detail: str


class NeedsReply(BaseModel):
    needs: list[NeedItem]
    slots: list[str]


def tidy(text: str, limit: int) -> str:
    """One plain line: no markup characters, no runs of space, cut at a word."""
    line = re.sub(r"\s+", " ", re.sub(r"[<>]", "", text.replace("&", " and "))).strip()
    if len(line) <= limit:
        return line
    cut = line[:limit].rsplit(" ", 1)[0]
    return (cut or line[:limit]).rstrip(",;:- ")


def kind_of(title: str) -> Kind:
    words = set(re.findall(r"[a-z]+", title.lower()))
    for kind, keys in KEYWORDS:
        if words & set(keys):
            return kind
    return "draft"


def predicate(goal: str) -> str:
    """The part of the goal after "need(s)/want(s)/to", where the things to get done are."""
    text = goal.strip().rstrip(".!?")
    found = re.search(
        r"\b(?:needs?|wants?|have to|has to|must|should|would like to)\b\s*", text, re.I
    )
    rest = text[found.end() :] if found else text
    return re.sub(r"^(?:to|that|us to)\s+", "", rest, flags=re.I).strip() or text


def split_goal(goal: str) -> list[str]:
    parts = re.split(
        r"\s*(?:,|;|\bthen\b|\bplus\b|\balso\b|\band\b)\s*", predicate(goal), flags=re.I
    )
    titles = [tidy(p, TITLE_MAX) for p in parts if len(p.strip()) > 2]
    return [t[0].upper() + t[1:] for t in titles if t][:MAX_NEEDS]


def rule_slots(deadline: datetime, now: datetime) -> list[str]:
    """Up to six morning and afternoon slots between now and the deadline, in UTC."""
    slots: list[str] = []
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    while len(slots) < MAX_SLOTS and day < deadline and day < now + timedelta(days=14):
        for hour in (10, 15):
            at = day.replace(hour=hour)
            if now + timedelta(hours=1) < at < deadline and len(slots) < MAX_SLOTS:
                slots.append(at.strftime("%a %d %b, %H:%M UTC"))
        day += timedelta(days=1)
    return slots


def rule_needs(goal: str, drafted: list[str]) -> list[NeedItem]:
    titles = [tidy(t, TITLE_MAX) for t in drafted if t.strip()][:MAX_NEEDS] or split_goal(goal)
    titles = [t[0].upper() + t[1:] for t in titles if t] or [tidy(predicate(goal), TITLE_MAX)]
    return [NeedItem(title=t, kind=kind_of(t), detail="Taken from the goal.") for t in titles]


def checked(reply: NeedsReply | None) -> list[NeedItem] | None:
    """The model's needs if they are usable: two to six, each with a plain title."""
    if reply is None:
        return None
    seen: set[str] = set()
    out: list[NeedItem] = []
    for item in reply.needs:
        title = tidy(item.title, TITLE_MAX)
        if not title or title.lower() in seen:
            continue
        seen.add(title.lower())
        out.append(NeedItem(title=title, kind=item.kind, detail=tidy(item.detail, DETAIL_MAX)))
    return out[:MAX_NEEDS] if len(out) >= 2 else None


def checked_slots(labels: list[str]) -> list[str]:
    out: list[str] = []
    for label in labels:
        line = tidy(label, 40)
        if line and line not in out:
            out.append(line)
    return out[:MAX_SLOTS]


async def make(engine: RoomEngine, coalition: str, state: State) -> None:
    """Make the needs and slots once, then let the Gardener loop seed them."""
    goal = str(state.charter["goal"])
    with engine.server.store.transaction(coalition) as tx:
        row = tx.execute(
            "SELECT needs FROM server_genesis WHERE coalition = ?", (coalition,)
        ).fetchone()
    drafted: list[str] = json.loads(row[0]) if row else []
    deadline = datetime.fromisoformat(str(state.charter["deadline"]).replace("Z", "+00:00"))
    now = datetime.fromtimestamp(engine.now(), UTC)
    items: list[NeedItem] | None = None
    slots: list[str] = []
    reply = None
    # A room built on a pack keeps the pack's own needs; the model only reads open goals.
    if not state.charter.get("pack"):
        reply = await ask(
            engine,
            coalition,
            "gardener",
            SYSTEM,
            {"goal": goal, "now": now.isoformat(), "deadline": deadline.isoformat()},
            NeedsReply,
            verb="reading",
            label="Reading the goal into needs",
        )
        items = checked(reply)
    source = "model" if items else "rules"
    if items and reply is not None:
        slots = checked_slots(reply.slots)
    else:
        items = rule_needs(goal, drafted)
    if not slots:
        slots = rule_slots(deadline, now)
    made: list[Document] = [
        {
            "id": derive_ulid("genesis-need", coalition, str(i)),
            "title": item.title,
            "kind": item.kind,
            "detail": item.detail,
        }
        for i, item in enumerate(items)
    ]
    with engine.server.store.transaction(coalition) as tx:
        tx.execute(
            "UPDATE server_genesis SET needs = ? WHERE coalition = ?",
            (json.dumps([n["title"] for n in made]), coalition),
        )

    def set_needs(doc: Document) -> None:
        doc["needs"] = made
        doc["slots"] = [{"id": f"s{i + 1}", "label": s} for i, s in enumerate(slots)]
        doc["needs_source"] = source
        doc["needs_state"] = "ready"

    engine.update(coalition, set_needs)
    engine.wake_gardener(coalition)
