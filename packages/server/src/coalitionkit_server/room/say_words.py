# SPDX-License-Identifier: Apache-2.0
"""What a reply to Say may add, and how a question is answered from what the room holds.

Code states the route ("Kept between you and your agent."). Whatever else the reply says must be
new: an answer taken from what the room actually knows, or a plain "I do not know that yet".
A model sentence that only repeats the route is dropped.
"""

from __future__ import annotations

import re

from coalitionkit_runtime.lifecycle import State

from ..adapter import Document

STARTS = re.compile(
    r"^(kept|sent|shared|noted|got it|done|ok|okay|sure|i kept|i sent|i shared)\b", re.I
)
QUESTION = re.compile(
    r"\?\s*$|^(who|what|when|where|which|how|is|are|do|does|can|will|why)\b", re.I
)
NOT_KNOWN = "I do not know that yet; nothing the room holds says."


def words(text: str) -> set[str]:
    return set(re.findall(r"[a-z]{3,}", text.lower()))


def adds(sentence: str, route_line: str) -> bool:
    """The sentence says something the route line does not."""
    if not sentence.strip() or STARTS.match(sentence.strip()):
        return False
    said, known = words(sentence), words(route_line)
    return bool(said) and len(said & known) / len(said) < 0.5


def is_question(text: str) -> bool:
    return bool(QUESTION.search(text.strip()))


def room_facts(state: State, doc: Document, labels: dict[str, str]) -> Document:
    """Everything a question can be answered from: all of it already shared in the room."""
    needs: list[Document] = []
    for n in doc["needs"]:
        task = state.tasks.get(n["id"])
        who = task.get("assignee") if task else None
        needs.append(
            {
                "title": n["title"],
                "what_done_looks_like": n["detail"],
                "status": task["status"] if task else "not yet a task",
                "taken_by": labels.get(who, who) if who else None,
            }
        )
    compared: Document = doc["compare"] or {}
    shared: list[str] = list(compared.get("slots") or [])
    names = {s["id"]: s["label"] for s in doc["slots"]}
    return {
        "goal": state.charter["goal"],
        "closes": state.charter["deadline"],
        "needs": needs,
        "times_everyone_can_do": [names.get(s, s) for s in shared],
    }


def rule_answer(text: str, facts: Document) -> str:
    """A plain answer from the facts, or plain ignorance."""
    said = words(text)
    for need in facts["needs"]:
        if said & words(need["title"]):
            who = need["taken_by"]
            held = f"{who} has it" if who else "nobody has it yet"
            return f"{need['title']}: {held}, and it is {need['status']}."
    if "time" in said or "when" in said or "slot" in said or "times" in said:
        times = facts["times_everyone_can_do"]
        if times:
            return "The times everyone can do: " + ", ".join(times) + "."
        return "No time that fits everyone has been found yet."
    return NOT_KNOWN
