# SPDX-License-Identifier: Apache-2.0
"""The fixed layout of each result kind: the tree code builds when the composer's fails.

Every card has something in it, and every kind uses the catalog part made for it: a budget is a
``CostSplit``, a list is a ``Checklist``, a schedule is a ``Timeline`` and a picture is an
``Image`` bound to the result's data model. Numbers are strings, except the minutes people
offered, which are bound ``{value, event_ref}`` to the signed offer they came from.
"""

from __future__ import annotations

from typing import Any, cast

from ..adapter import Document

#: Where an image result's picture sits in the result surface's data model.
IMAGE_SRC = "/image/src"


def card(index: int, title: str, fields: list[Document], prov: str) -> Document:
    return {
        "id": f"fx{index}",
        "component": "Card",
        "title": title,
        "fields": fields,
        "provenance": prov,
    }


def time_card(index: int, data: Document) -> Document | None:
    rows = data["time"] if data["amount"] is not None else data["rows"]
    if not rows:
        return None
    fields = [
        {
            "label": r["label"],
            "value": {"value": r["amount"], "event_ref": r["ref"]} if r["ref"] else "to be set",
        }
        for r in rows
    ]
    return card(index, "Time people offered, in minutes", fields, "signed")


def place_body(data: Document) -> list[Document]:
    if not data["options"]:
        hint = "Say a place in the Say box, for example: the hall is free on Saturday."
        fields = [{"label": "To name one", "value": hint}]
        return [card(0, "No place has been named yet", fields, "signed")]
    body: list[Document] = []
    for i, o in enumerate(data["options"]):
        fields = [{"label": "Why it fits", "value": o["why"]}]
        if o.get("check"):
            fields.append({"label": "Check first", "value": o["check"]})
            if o.get("url"):
                fields.append({"label": "Found on the web", "value": o["url"]})
        body.append(card(i, o["name"], fields, "estimate"))
    return body


def schedule_body(data: Document) -> list[Document]:
    body: list[Document] = []
    items = [
        {"start": s["start"], "end": s["end"], "title": s["title"], "state": "next"}
        for s in data["items"]
    ]
    if items:
        body.append({"id": "fxt", "component": "Timeline", "items": items})
        where = sorted({str(s["where"]) for s in data["items"]})
        body.append(card(0, "Where", [{"label": "Place", "value": ", ".join(where)}], "signed"))
    if data["steps"]:
        steps = [{"label": f"Step {n + 1}", "value": t} for n, t in enumerate(data["steps"])]
        body.append(card(1, "Order of steps", steps, "estimate"))
    return body


def budget_body(data: Document) -> list[Document]:
    body: list[Document] = []
    if data["amount"] is not None:
        unit = data["currency"]
        items = [
            {
                "label": r["label"],
                "payer": r["who"] or "shared",
                "amount": f"{r['amount']} {unit}",
                "kind": r["provenance"],
            }
            for r in data["rows"]
        ]
        split: Document = {"id": "fxc", "component": "CostSplit", "items": items}
        if data["how_shared"]:
            split["settlements"] = [data["how_shared"]]
        body.append(
            {
                "id": "fx0",
                "component": "Card",
                "title": f"Budget of {data['amount']} {unit}",
                "fields": [{"label": "Total", "value": f"{data['total']} {unit}"}],
                "provenance": "estimate",
                "children": ["fxc"],
            }
        )
        body.append(split)
    extra = time_card(1 if body else 0, data)
    if extra:
        body.append(extra)
    return body


def list_body(data: Document) -> list[Document]:
    items = [{"text": f"{i['label']} · {i['who']}", "done": False} for i in data["items"]]
    prov = data["items"][0]["provenance"] if data["items"] else "estimate"
    return [
        {
            "id": "fx0",
            "component": "Card",
            "title": "Who brings what",
            "provenance": prov,
            "children": ["fxl"],
        },
        {"id": "fxl", "component": "Checklist", "items": items},
    ]


def image_body(data: Document) -> list[Document]:
    if not data.get("hash"):
        why = str(data.get("why") or "The picture could not be made this time.")
        fields = [{"label": "Why", "value": why}]
        if data.get("prompt"):
            fields.append({"label": "What was to be drawn", "value": str(data["prompt"])})
        return [card(0, "No picture yet", fields, "model")]
    return [
        {
            "id": "fx0",
            "component": "Card",
            "title": str(data["alt"]),
            "provenance": "model",
            "children": ["fxi"],
        },
        {"id": "fxi", "component": "Image", "alt": str(data["alt"]), "src": {"path": IMAGE_SRC}},
    ]


def draft_body(data: Document) -> list[Document]:
    return [
        {
            "id": "fx0",
            "component": "Card",
            "title": data["subject"],
            "provenance": "estimate",
            "children": ["fxb"],
        },
        {"id": "fxb", "component": "Text", "text": data["body"]},
    ]


BODIES = {
    "place": place_body,
    "schedule": schedule_body,
    "budget": budget_body,
    "list": list_body,
    "image": image_body,
    "draft": draft_body,
}
#: Nodes that sit inside a card, not directly under the root.
INNER = {"fxb", "fxc", "fxl", "fxi"}


def fixed_body(kind: str, data: Document) -> list[Document]:
    """The cards code builds from the data: every one has something in it."""
    return BODIES.get(kind, draft_body)(data)


def fixed_tree(kind: str, title: str, detail: str, data: Document) -> list[Document]:
    """The tree code builds when the model's layout is missing or fails: always valid."""
    body = fixed_body(kind, data)
    head: list[Document] = [
        {"id": "h", "component": "Heading", "text": title, "variant": "h2"},
        {"id": "d", "component": "Text", "text": detail, "variant": "caption", "tone": "muted"},
    ]
    top = [n["id"] for n in body if n["id"] not in INNER]
    root: Document = {
        "id": "root",
        "component": "Column",
        "gap": "12",
        "children": ["h", "d", *top],
    }
    return [root, *head, *body]


def as_strings(value: Any) -> Any:
    """The data as a surface's data model: every number a string, nothing else changed."""
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, int | float):
        return str(cast(object, value))
    if isinstance(value, dict):
        mapping = cast(dict[Any, Any], value)
        return {str(cast(object, k)): as_strings(v) for k, v in mapping.items()}
    if isinstance(value, list):
        return [as_strings(v) for v in cast(list[Any], value)]
    return str(cast(object, value))


def surface_model(kind: str, data: Document) -> Document:
    """What a result's tree may bind to: its data with numbers as strings, and for a picture
    the host address it is served at (``/image/src``)."""
    model: Document = as_strings(data)
    if kind == "image" and data.get("hash"):
        model["image"] = {"src": f"/v1/room/media/{data['hash']}"}
    return model
