# SPDX-License-Identifier: Apache-2.0
"""Results: the budgets, schedules, lists, drafts and options an agent makes for a need.

A result is data in a fixed shape per kind plus a tree of catalog components. The model
(``composer``) may write the words and propose a tree; code decides what is fact. Anything the
model suggests carries ``provenance: "estimate"``; numbers and times come from signed offers and
the shared slots, never from the model; a number in a tree is ``{value, event_ref}`` on a real
event. A tree that fails ``compose_surface`` is asked for once more with the errors, then replaced
by a fixed tree built here.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseModel

from coalitionkit_surfaces import compose_surface

from ..adapter import Document
from .model import ask
from .needs import tidy

if TYPE_CHECKING:
    from .engine import RoomEngine

KINDS = ("place", "schedule", "budget", "list", "draft")
WHITELIST = {"Column", "Row", "Card", "Heading", "Text", "Badge", "Divider"}
MAX_ITEMS = 6

SYSTEM = (
    "You are one person's agent in a small group room, making the thing a need asks for. "
    "Reply with a title (under 60 characters), the data as a JSON text in the shape for the "
    "kind, and a tree of components. Kinds and data: place {options:[{name, why}]}, budget "
    "{rows:[{label, note}]}, list {items:[{label, who}]}, draft {subject, body}, schedule "
    "{items:[{title}]}. Everything you write is a suggestion for the group to judge; use only "
    "what the goal, the need, the plan and the offers say, never invent a fact, a price, a "
    "person or a place that is not given. Put no numbers in your tree. The tree is a flat list "
    "of nodes {id, component, props} where props is a JSON object text; the root has id "
    "'root'. Use only these components: Column and Row (props children: list of ids), Card "
    "(title), Heading (text, variant h3), Text (text, provenance 'estimate'), Badge (kind "
    "'estimate', label), Divider. Strings only, no markup."
)


class Node(BaseModel):
    id: str
    component: str
    props: str


class MadeReply(BaseModel):
    title: str
    data: str
    components: list[Node]


def slot_start(label: str, now: datetime) -> datetime | None:
    """The start time a slot label names ("Wed 5 Nov, 10:00 UTC"), in the year of ``now``."""
    found = re.search(r"(\d{1,2}) (\w{3}),? (\d{1,2}):(\d{2})", label)
    if not found:
        return None
    try:
        parsed = datetime.strptime(
            f"{found[1]} {found[2]} {now.year} {found[3]}:{found[4]}", "%d %b %Y %H:%M"
        ).replace(tzinfo=UTC)
    except ValueError:
        return None
    return parsed if parsed >= now - timedelta(days=200) else parsed.replace(year=now.year + 1)


def text(value: Any, limit: int) -> str:
    return tidy(str(value), limit) if isinstance(value, str | int | float) else ""


def rows_of(raw: Any, key: str) -> list[Document]:
    value: Any = cast(Document, raw).get(key) if isinstance(raw, dict) else None
    if not isinstance(value, list):
        return []
    return [cast(Document, r) for r in cast(list[Any], value) if isinstance(r, dict)][:MAX_ITEMS]


def echoes(label: str, facts: Document) -> bool:
    """The label only repeats the need or the goal, so it says nothing the room did not know."""
    said = set(re.findall(r"[a-z]{3,}", label.lower()))
    known = set(re.findall(r"[a-z]{3,}", f"{facts['need']['title']} {facts['goal']}".lower()))
    return not said or said <= known


def rule_data(kind: str, facts: Document) -> Document:
    """What code can say with no model: only what the room itself holds."""
    need = facts["need"]
    if kind == "place":
        return {"options": [], "chosen": None}
    if kind == "schedule":
        return {"items": schedule_items(facts, need["title"])}
    if kind == "budget":
        return budget_data(facts, [])
    if kind == "list":
        return list_data(facts, [])
    return {
        "subject": need["title"],
        "body": f"{facts['goal']}\n\nDone when: {need['detail']}",
    }


def schedule_items(facts: Document, title: str) -> list[Document]:
    now = datetime.fromisoformat(facts["now"])
    items: list[Document] = []
    for slot in facts["common"][:3]:
        start = slot_start(slot["label"], now)
        if start is None:
            continue
        end = start + timedelta(hours=1)
        items.append(
            {
                "title": title,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "where": "To be agreed",
            }
        )
    return items


def budget_data(facts: Document, suggested: list[Document]) -> Document:
    """Rows from signed offers (minutes each person said), then the model's rows as estimates."""
    rows: list[Document] = [
        {
            "label": f"{a['who']}: {a['title']}",
            "amount": a["minutes"],
            "provenance": "signed",
            "ref": a["offer_event"],
        }
        for a in facts["plan"]
    ]
    for row in suggested:
        label = text(row.get("label"), 60)
        if label and not echoes(label, facts):
            rows.append({"label": label, "amount": 0, "provenance": "estimate", "ref": None})
    return {
        "currency": "minutes",
        "rows": rows[: MAX_ITEMS * 2],
        "total": sum(r["amount"] for r in rows[: MAX_ITEMS * 2]),
    }


def list_data(facts: Document, suggested: list[Document]) -> Document:
    items: list[Document] = [
        {"label": a["title"], "who": a["who"], "provenance": "signed"} for a in facts["plan"]
    ]
    people = {a["who"] for a in facts["plan"]}
    for row in suggested:
        label = text(row.get("label"), 60)
        who = text(row.get("who"), 40)
        if label and not echoes(label, facts):
            items.append(
                {"label": label, "who": who if who in people else "", "provenance": "estimate"}
            )
    return {"items": items[: MAX_ITEMS * 2]}


def normalise(kind: str, raw: Any, facts: Document) -> Document | None:
    """The model's data made safe: shape fixed per kind, facts from code, the rest estimates."""
    if not isinstance(raw, dict):
        return None
    if kind == "place":
        options = [
            {
                "name": text(o.get("name"), 60),
                "why": text(o.get("why"), 120),
                "provenance": "estimate",
            }
            for o in rows_of(raw, "options")
        ]
        options = [o for o in options if o["name"] and not echoes(o["name"], facts)]
        return {"options": options, "chosen": None} if options else None
    if kind == "schedule":
        titles = rows_of(raw, "items")
        title = text(titles[0].get("title"), 60) if titles else ""
        return {"items": schedule_items(facts, title or facts["need"]["title"])}
    if kind == "budget":
        return budget_data(facts, rows_of(raw, "rows"))
    if kind == "list":
        data = list_data(facts, rows_of(raw, "items"))
        return data if data["items"] else None
    fields = cast(Document, raw)
    subject, body = text(fields.get("subject"), 100), tidy(str(fields.get("body", "")), 1500)
    return {"subject": subject, "body": body} if subject and body else None


def card(index: int, title: str, fields: list[Document], prov: str) -> Document:
    return {
        "id": f"fx{index}",
        "component": "Card",
        "title": title,
        "fields": fields,
        "provenance": prov,
    }


def fixed_body(kind: str, data: Document) -> list[Document]:
    """The cards code builds from the data: the facts, whatever the model's tree says."""
    body: list[Document] = []
    if kind == "place":
        for i, o in enumerate(data["options"]):
            why = [{"label": "Why", "value": o["why"], "provenance": "estimate"}]
            body.append(card(i, o["name"], why, "estimate"))
    elif kind == "schedule":
        for i, s in enumerate(data["items"]):
            fields = [
                {"label": "Start", "value": s["start"], "provenance": "signed"},
                {"label": "End", "value": s["end"], "provenance": "signed"},
                {"label": "Where", "value": s["where"], "provenance": "estimate"},
            ]
            body.append(card(i, s["title"], fields, "signed"))
    elif kind == "budget":
        fields = [
            {
                "label": r["label"],
                "value": {"value": r["amount"], "event_ref": r["ref"]} if r["ref"] else "to be set",
                "provenance": r["provenance"],
            }
            for r in data["rows"]
        ]
        body.append(card(0, f"Budget in {data['currency']}", fields, "signed"))
    elif kind == "list":
        fields = [
            {"label": i["label"], "value": i["who"] or "open", "provenance": i["provenance"]}
            for i in data["items"]
        ]
        body.append(card(0, "Items", fields, "signed"))
    else:
        body.append({"id": "fx0", "component": "Heading", "text": data["subject"], "variant": "h3"})
        body.append(
            {"id": "fx1", "component": "Text", "text": data["body"], "provenance": "estimate"}
        )
    return body


def fixed_tree(kind: str, title: str, detail: str, data: Document) -> list[Document]:
    """The tree code builds when the model's is missing or fails: always valid."""
    body = fixed_body(kind, data)
    head: list[Document] = [
        {"id": "h", "component": "Heading", "text": title, "variant": "h2"},
        {"id": "d", "component": "Text", "text": detail, "variant": "caption", "tone": "muted"},
    ]
    foot: list[Document] = [
        {
            "id": "f",
            "component": "Text",
            "text": "Suggestions are marked estimate. Signed rows come from offers people made.",
            "variant": "caption",
            "tone": "muted",
        }
    ]
    root: Document = {
        "id": "root",
        "component": "Column",
        "gap": "12",
        "children": ["h", "d", *[n["id"] for n in body], "f"],
    }
    return [root, *head, *body, *foot]


def with_facts(tree: list[Document], kind: str, data: Document) -> list[Document]:
    """The model's layout with the code-built facts added under its root, so a number or a
    time is always shown the way code built it."""
    body = fixed_body(kind, data)
    out = [dict(n) for n in tree]
    root = next((n for n in out if n["id"] == "root"), None)
    if root is None or not isinstance(root.get("children"), list):
        return tree
    root["children"] = [*root["children"], *[n["id"] for n in body]]
    return [*out, *body]


def parse_tree(nodes: list[Node]) -> list[Document] | str:
    """The model's nodes as components, or why they cannot be used."""
    out: list[Document] = []
    for n in nodes:
        if n.component not in WHITELIST:
            return f"component {n.component} is not allowed"
        try:
            props = json.loads(n.props)
        except ValueError:
            return f"props of {n.id} are not JSON"
        if not isinstance(props, dict):
            return f"props of {n.id} are not an object"
        out.append({"id": n.id, "component": n.component, **props})
    return out


def tree_errors(engine: RoomEngine, components: list[Document], known: set[str]) -> list[str]:
    return compose_surface(engine.catalog, "result", components, {}, known).errors


async def make(
    engine: RoomEngine,
    coalition: str,
    kind: str,
    assignee: str,
    task: str,
    facts: Document,
    known: set[str],
) -> tuple[str, Document, list[Document], str]:
    """(title, data, tree, source) for one result. Source is "model" when the model's own words
    stood as the data; the tree is the model's if it passed, else the fixed one."""
    errors: list[str] = []
    reply: MadeReply | None = None
    data: Document | None = None
    tree: list[Document] | None = None
    shown = {k: facts[k] for k in ("goal", "need", "plan", "common")}
    for _ in range(2):
        reply = await ask(
            engine,
            coalition,
            "composer",
            SYSTEM,
            {"kind": kind, "facts": shown, "errors_to_fix": errors},
            MadeReply,
            verb="making",
            label=f"Making {facts['need']['title']}",
            seat=assignee,
            need=task,
        )
        if reply is None:
            break
        data = data or normalise(kind, load(reply.data), facts)
        parsed = parse_tree(reply.components) if reply.components else []
        errors = [parsed] if isinstance(parsed, str) else tree_errors(engine, parsed, known)
        if parsed and not errors and not isinstance(parsed, str):
            tree = parsed
            break
        if not errors:
            break  # the model sent no tree; the fixed one is used
    source = "model" if data is not None else "rules"
    data = data if data is not None else rule_data(kind, facts)
    title = (
        tidy(reply.title, 60)
        if reply is not None and reply.title.strip()
        else facts["need"]["title"]
    )
    if tree is not None:
        tree = with_facts(tree, kind, data)
    return title, data, tree or fixed_tree(kind, title, facts["need"]["detail"], data), source


def load(raw: str) -> Any:
    try:
        return json.loads(raw)
    except ValueError:
        return None
