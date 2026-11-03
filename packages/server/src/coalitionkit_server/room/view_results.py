# SPDX-License-Identifier: Apache-2.0
"""The made things and the work of one viewer, as ``state.room`` shows them."""

from __future__ import annotations

from typing import TYPE_CHECKING

from coalitionkit_runtime.lifecycle import State
from coalitionkit_surfaces import compose_surface

from ..adapter import Document
from .work import can_mark_done, result_events

if TYPE_CHECKING:
    from .engine import RoomEngine


def visible_events(state: State, viewer: str) -> set[str]:
    return {k for k, e in state.events.items() if state.visible(e, viewer)}


def results_of(engine: RoomEngine, state: State, doc: Document, viewer: str) -> list[Document]:
    """Every result this viewer may see, with what replaced it when something did."""
    seen = visible_events(state, viewer)
    found = [(e, c) for e, c in result_events(state) if e["event_id"] in seen]
    latest: dict[str, str] = {}
    for event, content in found:
        latest[str(content["need_id"])] = str(event["event_id"])
    shown: list[Document] = []
    for index, (event, content) in enumerate(found):
        need = str(content["need_id"])
        later = next(
            (str(e["event_id"]) for e, c in found[index + 1 :] if c["need_id"] == need), None
        )
        successor = doc["successors"].get(need)
        replaced = later or (latest.get(str(successor), str(successor)) if successor else None)
        sources = [s for s in content["sources"] if isinstance(s, str)]
        messages = compose_surface(
            engine.catalog, f"result-{event['event_id']}", content["components"], {}, seen
        ).messages
        shown.append(
            {
                "id": event["event_id"],
                "need_id": need,
                "kind": content["kind"],
                "title": content["title"],
                "by": event["on_behalf_of"],
                "seq": event["seq"],
                "source": content["source"],
                "sources": sources,
                "seqs": [
                    state.events[s]["seq"] for s in sources if s in seen and s in state.events
                ],
                "tree": content["components"],
                "data": content["data"],
                "messages": messages,
                "replaced_by": replaced,
            }
        )
    return shown


def latest_by_need(results: list[Document]) -> dict[str, str]:
    return {str(r["need_id"]): str(r["id"]) for r in results}


def tasks_of(state: State, doc: Document, viewer: str, results: list[Document]) -> list[Document]:
    """The viewer's own tasks and what they can do about each."""
    latest = latest_by_need(results)
    titles = {n["id"]: n["title"] for n in doc["needs"]}
    return [
        {
            "task_id": task,
            "title": titles.get(task, ""),
            "status": t["status"],
            "result": latest.get(task),
            "can_mark_done": can_mark_done(state, doc, viewer, task),
        }
        for task, t in state.tasks.items()
        if t.get("assignee") == viewer and task in titles
    ]


def change_of(state: State, doc: Document) -> Document | None:
    """The latest change: who asked, what it touched, who is asked, and how much stood still."""
    change = doc["change"]
    if change is None:
        return None
    moved = set(change["moved"])
    asked = sorted(
        {
            d
            for s in state.subjects.values()
            if s["kind"] in {"plan", "tension_option"}
            and s.get("status") == "pending"
            and set(s["tasks"]) & moved
            for d in s["deciders"]
        }
    )
    gone = moved | {
        str(n["replaces"]) for n in doc["needs"] if n["id"] in moved and n.get("replaces")
    }
    untouched = sum(1 for n in doc["needs"] if n["id"] not in gone)
    return {
        "from": change["from"],
        "text": change["text"],
        "moved": list(change["moved"]),
        "asked": asked,
        "untouched": untouched,
    }
