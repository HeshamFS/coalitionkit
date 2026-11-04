# SPDX-License-Identifier: Apache-2.0
"""Results: the finished thing a need asks for, and how it is shown.

Two steps. ``makers`` does the real work for the kind (a message someone could send, a budget
that adds up, kinds of place with what to check, a list of who brings what). This module then
turns that data into a tree of catalog components: the ``composer`` only chooses how to show the
data, and code checks that the tree shows all of it, drops empty cards and passes
``compose_surface``; if the model's layout fails (asked once more with the errors) a fixed tree
built from the same data is used. Numbers that are facts come from signed offers and carry
``{value, event_ref}`` on those offers; anything the model suggested is an estimate, said once
at the card.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseModel

from coalitionkit_surfaces import compose_surface

from ..adapter import Document
from . import image, makers
from .fixed import fixed_tree, surface_model, time_card
from .model import ask
from .needs import slot_start, tidy

if TYPE_CHECKING:
    from .engine import RoomEngine

KINDS = ("place", "schedule", "budget", "list", "draft", "image")
WHITELIST = {
    *("Column", "Row", "Card", "Heading", "Text", "Badge", "Divider"),
    *("Checklist", "CostSplit", "Timeline", "Gantt", "KeyValue", "Table", "List"),
    *("Meter", "Deadline", "Image"),
}
MAX_ITEMS = 6

LAYOUT_SYSTEM = (
    "You choose how to show a finished thing to a small group. You are given its data; show "
    "all of it, none of it changed. Reply with a title taken from the need or the content "
    "(never starting with 'Suggestion') and a flat list of nodes {id, component, props}, props "
    "a JSON object text, the root with id 'root'. Components: Column and Row (children: list "
    "of ids), Card (title, fields: [{label, value}] with plain-string values, children, "
    "provenance), Heading (text, variant h3), Text (text), Badge (kind, label), Divider. Put "
    "one Card per group of related lines and set the card's provenance once ('estimate' for "
    "everything the data marks as a suggestion); do not repeat it on every line. Never make an "
    "empty card. Write every number inside a string; no number may stand alone. Strings only, "
    "no markup. A message goes in one Card whose child is a Text holding the whole message. "
    "This is for people: never show an id, a kind or an empty value. Richer parts, each with "
    "exactly these props: CostSplit (items: [{label, payer, amount, kind}] with amount a "
    "string such as '60 EUR', settlements: [strings]); Checklist (items: [{text, done}], done "
    "false); Timeline (items: [{start, end, title, state}], start and end ISO times, state "
    "'next'); Gantt (rows: [{task, assignee, start, end, status}]); KeyValue (pairs: [{label, "
    "value}]); Table (columns: [{key, label}], rows: {path} naming a list in the data, such "
    "as {'path': '/items'}); List (items: {path}); Deadline (label, consequence, deadline "
    "ISO). Put a rich part inside a Card's children so the card carries the title and the "
    "provenance. A budget shows its lines in a CostSplit, a list in a Checklist whose text "
    "names who brings each item, a schedule in a Timeline or a Gantt."
)
INTERNAL_LABELS = {"id", "kind", "chosen", "need", "need_id", "provenance", "source"}
EMPTY_VALUES = {"", "null", "none", "undefined", "[]", "{}"}


class Node(BaseModel):
    id: str
    component: str
    props: str


class LayoutReply(BaseModel):
    title: str
    components: list[Node]


def echoes(label: str, facts: Document) -> bool:
    """The label only repeats the need or the goal, so it says nothing the room did not know."""
    said = set(re.findall(r"[a-z]{3,}", label.lower()))
    known = set(re.findall(r"[a-z]{3,}", f"{facts['need']['title']} {facts['goal']}".lower()))
    return not said or said <= known


def schedule_items(facts: Document, titles: list[str]) -> list[Document]:
    """One entry per shared time, in order, each taking the next step (or the need's title)."""
    now = datetime.fromisoformat(facts["now"])
    items: list[Document] = []
    for index, slot in enumerate(facts["common"][:3]):
        start = slot_start(slot["label"], now)
        if start is None:
            continue
        title = titles[index] if index < len(titles) else facts["need"]["title"]
        items.append(
            {
                "title": title,
                "start": start.isoformat(),
                "end": (start + timedelta(hours=1)).isoformat(),
                "where": "To be confirmed",
            }
        )
    return items


def time_rows(facts: Document) -> list[Document]:
    """What people offered, in minutes: each number is bound to the offer it came from."""
    return [
        {
            "label": f"{a['who']}: {a['title']}",
            "amount": a["minutes"],
            "provenance": "signed",
            "ref": a["offer_event"],
        }
        for a in facts["plan"]
    ][: MAX_ITEMS * 2]


def budget_data(facts: Document, made: Document | None) -> Document:
    """A budget in the stated amount when there is one, else a time budget from the offers."""
    signed = time_rows(facts)
    minutes = sum(r["amount"] for r in signed)
    wanted = facts["amount"]
    if wanted is None:
        return {
            "currency": "minutes",
            "amount": None,
            "rows": signed,
            "how_shared": "",
            "suggested": [],
            "time": [],
            "time_total": minutes,
            "total": minutes,
        }
    rows = [{**line, "provenance": "estimate"} for line in (made or {}).get("lines", [])] or [
        {
            "label": "Total available",
            "amount": wanted["amount"],
            "who": "not yet split",
            "provenance": "estimate",
        }
    ]
    return {
        "currency": wanted["unit"],
        "amount": wanted["amount"],
        "rows": rows,
        "how_shared": (made or {}).get("how_shared", ""),
        "suggested": [],
        "time": signed,
        "time_total": minutes,
        "total": sum(int(r["amount"]) for r in rows),
    }


def draft_by_rules(facts: Document) -> Document:
    """A complete message built from what the room knows, with the open points said as such.

    The shared free times are when the people can meet, never when the event is, so the
    message does not give them as the time."""
    names = " and ".join(facts["people"][:3]) or "the organisers"
    body = (
        "Hello,\n\nWe would love you to join us.\n\n"
        "When: the time is still to be confirmed.\nWhere: the place is still to be confirmed.\n\n"
        "Please reply to say whether you can come, and tell us if you have ideas or can help.\n\n"
        f"Thanks,\n{names}"
    )
    return {"subject": tidy(facts["need"]["title"], 100), "body": body}


def data_for(kind: str, made: Document | None, facts: Document) -> Document:
    """The result's data: the maker's work where it stood, else what code can honestly say."""
    if kind == "place":
        ideas = (made or {}).get("ideas", [])
        options = [{"provenance": "estimate", **i} for i in ideas if not echoes(i["name"], facts)]
        return {"options": options, "chosen": None, **web_of(made)}
    if kind == "budget":
        return budget_data(facts, made)
    if kind == "schedule":
        steps = [s for s in (made or {}).get("steps", [])]
        return {"items": schedule_items(facts, steps), "steps": steps}
    if kind == "list":
        if made:
            items = [{**i, "provenance": "estimate"} for i in made["items"]]
            return {"items": items, **web_of(made)}
        return {
            "items": [
                {"label": a["title"], "who": a["who"], "provenance": "signed"}
                for a in facts["plan"]
            ]
        }
    return made or draft_by_rules(facts)


def web_of(made: Document | None) -> Document:
    """The pages a web search found for this result, kept with its data when there are any."""
    return {"web": made["web"]} if made and made.get("web") else {}


def parse_tree(nodes: list[Node]) -> list[Document] | str:
    """The model's nodes as components, with empty cards dropped, or why they cannot be used."""
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
        out.append({"id": n.id, "component": n.component, **cast(Document, props)})
    return drop_empty(out)


def drop_empty(tree: list[Document]) -> list[Document]:
    """No card without a title, fields or children; the parents forget the dropped ids."""
    gone = {
        n["id"]
        for n in tree
        if n["component"] == "Card" and not (n.get("fields") or n.get("children"))
    }
    out: list[Document] = []
    for n in tree:
        if n["id"] in gone:
            continue
        kids = n.get("children")
        if isinstance(kids, list):
            n = {**n, "children": [k for k in cast(list[Any], kids) if k not in gone]}
        out.append(n)
    return out


def reachable(tree: list[Document]) -> list[Document]:
    """The nodes a viewer can reach from the root, through children, in tree order."""
    by_id = {n["id"]: n for n in tree}
    seen: set[str] = set()
    stack = ["root"]
    while stack:
        node = by_id.get(stack.pop())
        if node is None or node["id"] in seen:
            continue
        seen.add(node["id"])
        kids = node.get("children")
        if isinstance(kids, list):
            stack.extend(str(k) for k in cast(list[Any], kids))
    return [n for n in tree if n["id"] in seen]


def shown_text(tree: list[Document]) -> str:
    return json.dumps(reachable(tree), ensure_ascii=False).lower()


#: The part each kind is shown in: a layout without it is asked for again.
PREFERRED = {"budget": "CostSplit", "list": "Checklist"}


def covers(tree: list[Document], kind: str, data: Document) -> str | None:
    """None if the tree shows all of the data in the part made for it, else what is missing."""
    seen = shown_text(tree)
    part = PREFERRED.get(kind)
    if part and not any(n["component"] == part for n in reachable(tree)):
        return f"show the {kind} in a {part}"
    wanted: list[str] = []
    if kind == "place":
        wanted = [o["name"] for o in data["options"]]
    elif kind == "list":
        wanted = [i["label"] for i in data["items"]]
    elif kind == "budget":
        wanted = [r["label"] for r in data["rows"]]
    elif kind == "draft":
        wanted = [data["subject"], data["body"][:40]]
    elif (
        kind == "image"
        and data.get("hash")
        and not any(n["component"] == "Image" for n in reachable(tree))
    ):
        return "the layout leaves out the picture"
    for item in wanted:
        if json.dumps(item[:14].lower(), ensure_ascii=False)[1:-1] not in seen:
            return f"the layout leaves out: {item}"
    return None


#: A layout may not say that something was agreed: beyond the signed plan nobody agreed anything.
SAYS_AGREED = re.compile(
    r"\b(?:is|are|was|were|been|now|all|we|they|everyone)\s+(?:agreed|decided|confirmed)\b", re.I
)


def claims_agreement(tree: list[Document], data: Document) -> str | None:
    """The layout says something was agreed that the data does not say, or None."""
    said = SAYS_AGREED.search(shown_text(tree))
    if said and said[0].lower() not in json.dumps(data, ensure_ascii=False).lower():
        return "nobody has agreed this yet: do not write that it was agreed, decided or confirmed"
    return None


def shows_internals(tree: list[Document], need_id: str) -> str | None:
    """What a person should not be shown, or None. The model can ignore the prompt; code cannot."""
    if need_id and need_id.lower() in shown_text(tree):
        return "do not show the id of the need"
    for node in reachable(tree):
        fields = cast(list[Document], node.get("fields") or [])
        for field in fields:
            label = str(field.get("label", "")).strip().lower()
            value = str(field.get("value", "")).strip().lower()
            if label in INTERNAL_LABELS or value in EMPTY_VALUES:
                return f"do not show the field '{label}': it means nothing to a person"
    return None


def tree_errors(
    engine: RoomEngine, components: list[Document], known: set[str], model: Document | None = None
) -> list[str]:
    """Every reason the tree fails the catalog, its bindings checked against the data model."""
    return compose_surface(engine.catalog, "result", components, model or {}, known).errors


def append_time(tree: list[Document], kind: str, data: Document) -> list[Document]:
    """The signed time section is added by code next to the model's layout, numbers bound."""
    if kind != "budget" or data["amount"] is None:
        return tree
    extra = time_card(9, data)
    root = next((n for n in tree if n["id"] == "root"), None)
    if extra is None or root is None or not isinstance(root.get("children"), list):
        return tree
    root["children"] = [*root["children"], extra["id"]]
    return [*tree, extra]


async def layout(
    engine: RoomEngine,
    coalition: str,
    kind: str,
    assignee: str,
    task: str,
    facts: Document,
    data: Document,
    known: set[str],
) -> tuple[str, list[Document]] | None:
    """The composer's layout of the data, if it passes every check; else None."""
    shown = {
        k: v
        for k, v in data.items()
        if k not in {"time", "time_total", "web"} and v not in (None, "", [], {})
    }
    need = {k: facts["need"][k] for k in ("title", "detail")}
    errors: list[str] = []
    for _ in range(2):
        reply = await ask(
            engine,
            coalition,
            "composer",
            LAYOUT_SYSTEM,
            {"kind": kind, "need": need, "data": shown, "fix_this": errors},
            LayoutReply,
            verb="making",
            label=f"Laying out {facts['need']['title']}",
            seat=assignee,
            need=task,
            effort="low",
        )
        if reply is None:
            return None
        parsed = parse_tree(reply.components)
        title = tidy(reply.title, 60)
        if isinstance(parsed, str):
            errors = [parsed]
        elif not title or title.lower().startswith("suggestion"):
            errors = ["give a title from the need or the content, not 'Suggestion'"]
        else:
            errors = tree_errors(engine, parsed, known, surface_model(kind, data))
            hidden = [n["id"] for n in parsed if n not in reachable(parsed)]
            if hidden and not errors:
                errors = [f"these nodes are not reachable from root: {', '.join(hidden)}"]
            missing = (
                covers(parsed, kind, data)
                or shows_internals(parsed, facts["need"]["id"])
                or claims_agreement(parsed, data)
            )
            if missing and not errors:
                errors = [missing]
            if not errors and parsed:
                return title, append_time(parsed, kind, data)
    return None


def title_for(kind: str, data: Document, need: Document) -> str:
    if kind == "budget" and data["amount"] is None:
        return "Time budget"
    if kind == "budget":
        return f"Budget of {data['amount']} {data['currency']}"
    if kind == "place" and not data["options"]:
        return "No place has been named yet"
    return need["title"]


async def make(
    engine: RoomEngine,
    coalition: str,
    kind: str,
    assignee: str,
    task: str,
    facts: Document,
    known: set[str],
) -> tuple[str, Document, list[Document], str]:
    """(title, data, tree, source). The data is the maker's work when it stood ("model"), else
    what code can say ("rules"); the tree is the composer's layout when it passes, else fixed."""
    if kind == "image":
        sink = image.activity_sink(engine, coalition)
        data, source = await image.make_image(engine, coalition, assignee, task, facts, sink)
        title = facts["need"]["title"]
        return title, data, fixed_tree(kind, title, facts["need"]["detail"], data), source
    made = await makers.make_data(engine, coalition, kind, assignee, task, facts)
    data = data_for(kind, made, facts)
    source = "model" if made is not None and not made.get("by_rules") else "rules"
    title = title_for(kind, data, facts["need"])
    shown = None
    needs_layout = (kind == "place" and data["options"]) or kind == "list"
    if needs_layout or (kind == "budget" and data["amount"] is not None):
        shown = await layout(engine, coalition, kind, assignee, task, facts, data, known)
    if shown is not None:
        title, tree = shown
        if kind == "place" and not data["options"]:
            title = "No place has been named yet"
        return title, data, tree, source
    return title, data, fixed_tree(kind, title, facts["need"]["detail"], data), source
