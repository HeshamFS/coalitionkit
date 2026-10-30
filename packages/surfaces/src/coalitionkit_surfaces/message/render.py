# SPDX-License-Identifier: Apache-2.0
"""Turn one viewer's validated A2UI tree into plain text sections and numbered options.

Only components that list the ``message`` door render. Others show their declared ``summary``
or are left out with a fixed line. Values are text; a number carries its source event; nothing
marked as coming from a vault appears. Nothing here calls a model.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, cast

from ..a2ui import ROOT_ID
from .doors import Doors, on_message_door

Document = dict[str, Any]

NOT_SHOWN = "Some items are not shown in text."
WITHHELD = "A private value is not shown."
INVALID_VIEW = "Your view cannot be shown in text right now."

MAX_DEPTH = 24
MAX_RECORDS = 25
HEAD_KEYS = ("title", "label", "text", "question", "what", "alt")
BODY_KEYS = (
    "body", "description", "summary", "consequence", "consequenceOfNo", "yourPart", "cost",
    "reason", "rule", "empty", "receipt", "markdown", "next", "period",
)  # fmt: skip
LABELLED = {"status": "Status", "state": "State"}
DATED = {
    "decision_deadline": "Decide by",
    "deadline": "Deadline",
    "by": "By",
    "expires": "Expires",
}
LAYOUT_NUMBERS = frozenset({"columns", "gap", "max", "min", "step", "maxLength", "size"})
LIST_KEYS = (
    "fields", "pairs", "items", "rows", "diff", "remaining", "others", "constraints",
    "conditions", "params",
)  # fmt: skip
OPTION_KEYS = ("options", "choices")
LINK_KEYS = ("child", "children", "panels")
RECORD_LABELS = ("label", "key", "title", "text", "name")


@dataclass(frozen=True)
class Option:
    """One numbered choice. Kind ``answer`` is a typed answer; ``confirm`` can only open the
    trusted confirm step for ``subject`` (with ``option_id`` as the choice)."""

    number: int
    label: str
    kind: Literal["answer", "confirm"]
    component_id: str
    option_id: str
    subject: Document | None = None


@dataclass(frozen=True)
class Section:
    """The text of one top-level item of the tree, without option numbers (so it stays stable)."""

    key: str
    text: str


@dataclass(frozen=True)
class Rendered:
    sections: list[Section] = field(default_factory=lambda: list[Section]())
    options: list[Option] = field(default_factory=lambda: list[Option]())

    def options_block(self) -> str:
        if not self.options:
            return ""
        lines = [f"{o.number}. {o.label}" for o in self.options]
        return "\n".join(["Reply with one number:", *lines])


def clean(text: str) -> str:
    """Text only: control characters go, newlines stay."""
    return "".join(ch for ch in text if ch == "\n" or ch.isprintable()).strip()


def is_vault(item: Any) -> bool:
    """True for a node or record whose provenance says its content comes from a vault."""
    body = _doc(item)
    return body is not None and str(body.get("provenance", "")).strip().lower() == "vault"


def _doc(value: Any) -> Document | None:
    return cast(Document, value) if isinstance(value, dict) else None


def _is_bound(value: Any) -> bool:
    body = _doc(value)
    return body is not None and set(body) == {"value", "event_ref"}


def lookup(data: Any, path: str) -> Any:
    """The value at an absolute JSON pointer in the data model, or ``None``."""
    current: Any = data
    for raw in path.split("/")[1:]:
        key = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            items = cast(list[Any], current)
            current = items[int(key)] if key.isdigit() and int(key) < len(items) else None
        elif (mapping := _doc(current)) is not None:
            current = mapping.get(key)
        else:
            return None
    return current


class _Renderer:
    def __init__(self, nodes: Mapping[str, Document], data: Any, doors: Doors) -> None:
        self.nodes, self.data, self.doors = nodes, data, doors
        self.options: list[Option] = []
        self.hidden = False
        self.withheld = False

    # -- values -------------------------------------------------------------------------------

    def value(self, raw: Any) -> Any:
        body = _doc(raw)
        if body is not None and set(body) == {"path"} and isinstance(body["path"], str):
            return lookup(self.data, body["path"])
        return raw

    def fmt(self, raw: Any) -> str:
        value = self.value(raw)
        if isinstance(value, str):
            return clean(value)
        if isinstance(value, bool):
            return "yes" if value else "no"
        if _is_bound(value):
            bound = cast(Document, value)
            return f"{bound['value']} [src {clean(str(bound['event_ref']))}]"
        return ""

    def records(self, raw: Any) -> list[Document | str]:
        value = self.value(raw)
        if not isinstance(value, list):
            return []
        return [r for r in cast(list[Any], value) if isinstance(r, str | dict)]

    # -- lines --------------------------------------------------------------------------------

    def record_line(self, record: Document | str) -> str:
        if isinstance(record, str):
            return clean(record)
        if is_vault(record):
            self.withheld = True
            return ""
        label = next((self.fmt(record[k]) for k in RECORD_LABELS if self.fmt(record.get(k))), "")
        value = self.fmt(record.get("value"))
        if label and value:
            return f"{label}: {value}"
        if label or value:
            return label or value
        scalars = [self.fmt(v) for k, v in record.items() if k != "provenance"]
        return ", ".join(s for s in scalars if s)

    def own_lines(self, node_id: str, node: Document) -> list[str]:
        lines: list[str] = []
        head = next((self.fmt(node[k]) for k in HEAD_KEYS if self.fmt(node.get(k))), "")
        if head:
            lines.append(head)
        lines += [text for key in BODY_KEYS if (text := self.fmt(node.get(key)))]
        for labels in (LABELLED, DATED):
            for key, label in labels.items():
                if text := self.fmt(node.get(key)):
                    lines.append(f"{label}: {text}")
        for key, raw in node.items():
            if key not in LAYOUT_NUMBERS and _is_bound(self.value(raw)):
                lines.append(f"{key}: {self.fmt(raw)}")
        for key in LIST_KEYS:
            found = self.records(node.get(key))
            lines += [line for r in found[:MAX_RECORDS] if (line := self.record_line(r))]
            if len(found) > MAX_RECORDS:
                lines.append(f"...and {len(found) - MAX_RECORDS} more")
        self.add_options(node_id, node, head)
        return lines

    def add_options(self, node_id: str, node: Document, head: str) -> None:
        name = str(node.get("component"))
        subject = _doc(node.get("subject"))
        if name == "ConsentCard" and subject is not None:
            about = self.fmt(node.get("summary")) or self.fmt(node.get("consequence")) or head
            label = "Open the confirm step" + (f" for: {about[:60]}" if about else "")
            self.push(label, "confirm", node_id, str(subject["id"]), subject)
            return
        for key in OPTION_KEYS:
            for record in self.records(node.get(key)):
                option = _doc(record)
                label = self.record_line(record)
                ident = str(option.get("id", option.get("option_id", ""))) if option else label
                ident = ident or label
                if not (label and ident):
                    continue
                if name == "TensionCard" and subject is not None:
                    text = f"{label} (opens the confirm step)"
                    self.push(text, "confirm", node_id, ident, subject)
                else:
                    self.push(label, "answer", node_id, ident, None)

    def push(
        self,
        label: str,
        kind: Literal["answer", "confirm"],
        component_id: str,
        option_id: str,
        subject: Document | None,
    ) -> None:
        number = len(self.options) + 1
        self.options.append(Option(number, label, kind, component_id, option_id, subject))

    # -- the tree -----------------------------------------------------------------------------

    def children(self, node: Document) -> list[str]:
        found: list[str] = []
        for key in LINK_KEYS:
            value = node.get(key)
            if isinstance(value, str):
                found.append(value)
            elif isinstance(value, list):
                found += [c for c in cast(list[Any], value) if isinstance(c, str)]
        return [c for c in found if c in self.nodes]

    def lines(self, node_id: str, depth: int = 0) -> list[str]:
        node = self.nodes[node_id]
        if is_vault(node):  # first: before the summary, the own fields, options and children
            self.withheld = True
            return []
        if not on_message_door(self.doors, str(node.get("component"))):
            summary = self.fmt(node.get("summary"))
            self.hidden = self.hidden or not summary
            return [summary] if summary else []
        lines = self.own_lines(node_id, node)
        if depth < MAX_DEPTH:
            for child in self.children(node):
                lines += self.lines(child, depth + 1)
        return lines

    def section(self, node_id: str, *, own_only: bool = False) -> Section:
        self.hidden = self.withheld = False
        node = self.nodes[node_id]
        if is_vault(node):
            self.withheld = True
            lines: list[str] = []
        elif not own_only:
            lines = self.lines(node_id)
        elif on_message_door(self.doors, str(node.get("component"))):
            lines = self.own_lines(node_id, node)
        else:
            lines = []
        if self.hidden:
            lines.append(NOT_SHOWN)
        if self.withheld:
            lines.append(WITHHELD)
        return Section(node_id, "\n".join(lines))


def render_tree(components: list[Document], data_model: Any, doors: Doors) -> Rendered:
    """Text sections (one per top-level item) and numbered options for one validated tree."""
    nodes = {str(c["id"]): c for c in components}
    renderer = _Renderer(nodes, data_model, doors)
    root = nodes[ROOT_ID]
    if is_vault(root):  # a withheld root withholds its whole subtree
        return Rendered([Section(ROOT_ID, WITHHELD)], [])
    kids = renderer.children(root)
    sections: list[Section] = []
    if kids:
        sections.append(renderer.section(ROOT_ID, own_only=True))
        sections += [renderer.section(kid) for kid in kids]
    else:
        sections.append(renderer.section(ROOT_ID))
    return Rendered([s for s in sections if s.text], renderer.options)
