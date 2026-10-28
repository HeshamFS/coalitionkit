# SPDX-License-Identifier: Apache-2.0
"""The closed component catalog and the validator every A2UI tree passes before it is sent."""

from __future__ import annotations

import json
import re
from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from .a2ui import A2UI_VERSION, CATALOG_ID, ROOT_ID

Document = dict[str, Any]

MAX_COMPONENTS = 500
MAX_DEPTH = 24
_ID = re.compile(r"[A-Za-z0-9_.-]{1,64}")
_HTML = re.compile(r"<\s*[/!?A-Za-z]|&(#[0-9]+|#[xX][0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]*);")
_RESERVED = frozenset({"id", "component"})
_BOUND_KEYS = frozenset({"value", "event_ref"})


@dataclass(frozen=True)
class ComponentSpec:
    props: frozenset[str]
    required: frozenset[str]
    doors: frozenset[str]


@dataclass(frozen=True)
class Catalog:
    catalog_id: str
    components: dict[str, ComponentSpec]


def load_catalog(path: str | Path) -> Catalog:
    """Read a catalog definition: ``{catalog_id, components: {Name: {props, required, doors}}}``.

    ``doors`` are the props that hold the ids of other components (``child``, ``children``).
    """
    data = _as_doc(json.loads(Path(path).read_text(encoding="utf-8")))
    specs = _as_doc(data.get("components")) if data is not None else None
    if data is None or specs is None:
        raise ValueError("catalog file needs a components object")
    catalog_id = data.get("catalog_id", CATALOG_ID)
    if not isinstance(catalog_id, str) or not catalog_id:
        raise ValueError("catalog_id must be a string")
    components: dict[str, ComponentSpec] = {}
    for name, spec in specs.items():
        body = _as_doc(spec)
        if body is None:
            raise ValueError(f"component {name} must be an object")
        doors = frozenset(str(x) for x in body.get("doors", []))
        props = frozenset(str(x) for x in body.get("props", [])) | doors
        required = frozenset(str(x) for x in body.get("required", []))
        if not required <= props:
            raise ValueError(f"component {name} requires props it does not allow")
        components[name] = ComponentSpec(props, required, doors)
    return Catalog(catalog_id, components)


def _as_doc(value: Any) -> Document | None:
    return cast(Document, value) if isinstance(value, dict) else None


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _is_bound(value: Any) -> bool:
    body = _as_doc(value)
    return (
        body is not None
        and frozenset(body) == _BOUND_KEYS
        and _is_number(body["value"])
        and isinstance(body["event_ref"], str)
        and bool(body["event_ref"])
    )


def _walk(value: Any, where: str, known: Collection[str] | None, errors: list[str]) -> None:
    if isinstance(value, str):
        if _HTML.search(value):
            errors.append(f"{where}: html in a string")
    elif _is_bound(value):
        ref: str = value["event_ref"]
        if known is not None and ref not in known:
            errors.append(f"{where}: number bound to unknown event {ref}")
    elif _is_number(value):
        errors.append(f"{where}: number not bound to a source event")
    elif (mapping := _as_doc(value)) is not None:
        if frozenset(mapping) == _BOUND_KEYS:
            errors.append(f"{where}: malformed bound number")
        for key, item in mapping.items():
            _walk(key, f"{where} key", known, errors)
            _walk(item, f"{where}.{key}", known, errors)
    elif isinstance(value, list):
        for index, item in enumerate(value):  # pyright: ignore[reportUnknownArgumentType, reportUnknownVariableType]
            _walk(item, f"{where}[{index}]", known, errors)
    elif value is not None and not isinstance(value, bool):
        errors.append(f"{where}: unsupported value")


def _links(spec: ComponentSpec, node: Document, where: str, errors: list[str]) -> list[str]:
    links: list[str] = []
    for door in sorted(spec.doors & set(node)):
        value = node[door]
        if door == "children" and not isinstance(value, list):
            errors.append(f"{where}.{door}: must be a list of component ids")
            continue
        items: list[Any] = value if isinstance(value, list) else [value]  # pyright: ignore[reportUnknownVariableType]
        for item in items:
            if isinstance(item, str) and _ID.fullmatch(item):
                links.append(item)
            else:
                errors.append(f"{where}.{door}: not a component id")
    return links


def _check_node(
    catalog: Catalog, node: Any, index: int, known: Collection[str] | None, errors: list[str]
) -> tuple[str, list[str]] | None:
    where = f"components[{index}]"
    if not isinstance(node, dict):
        errors.append(f"{where}: not an object")
        return None
    item: Document = node  # pyright: ignore[reportUnknownVariableType]
    ident = item.get("id")
    if not isinstance(ident, str) or not _ID.fullmatch(ident):
        errors.append(f"{where}: bad id")
        return None
    where = f"component {ident}"
    spec = catalog.components.get(str(item.get("component")))
    if spec is None:
        errors.append(f"{where}: unknown component {item.get('component')!r}")
        return None
    for prop in sorted(set(item) - _RESERVED - spec.props):
        errors.append(f"{where}: prop {prop} not allowed")
    for prop in sorted(spec.required - set(item)):
        errors.append(f"{where}: missing required prop {prop}")
    links = _links(spec, item, where, errors)
    for prop, value in item.items():
        if prop not in spec.doors and prop not in _RESERVED:
            _walk(value, f"{where}.{prop}", known, errors)
    return ident, links


def _graph_errors(edges: dict[str, list[str]]) -> list[str]:
    errors: list[str] = []
    referenced = {child for children in edges.values() for child in children}
    for child in sorted(referenced - set(edges)):
        errors.append(f"reference to missing component {child}")
    roots = sorted(set(edges) - referenced)
    if ROOT_ID not in edges:
        errors.append(f"no component with id {ROOT_ID}")
        return errors
    if len(roots) > 1:
        errors.append(f"more than one root: {', '.join(roots)}")
    depth: dict[str, int] = {}
    stack: set[str] = set()

    def visit(node: str) -> int:
        if node in stack:
            errors.append(f"cycle through {node}")
            return 0
        if node in depth:
            return depth[node]
        stack.add(node)
        deepest = 1 + max((visit(c) for c in edges[node] if c in edges), default=0)
        stack.discard(node)
        depth[node] = deepest
        return deepest

    levels = visit(ROOT_ID)
    for orphan in sorted(set(edges) - set(depth)):
        if orphan not in roots:
            errors.append(f"orphan component {orphan}")
    if levels > MAX_DEPTH and not any(e.startswith("cycle") for e in errors):
        errors.append(f"depth {levels} over {MAX_DEPTH}")
    return errors


def validate_components(
    catalog: Catalog, components: Any, known_events: Collection[str] | None = None
) -> list[str]:
    """Every reason the tree must not be sent. An empty list means it passes."""
    if not isinstance(components, list):
        return ["components must be a list"]
    nodes: list[Any] = components  # pyright: ignore[reportUnknownVariableType]
    if len(nodes) > MAX_COMPONENTS:
        return [f"{len(nodes)} components over {MAX_COMPONENTS}"]
    errors: list[str] = []
    edges: dict[str, list[str]] = {}
    for index, node in enumerate(nodes):
        checked = _check_node(catalog, node, index, known_events, errors)
        if checked is None:
            continue
        if checked[0] in edges:
            errors.append(f"duplicate id {checked[0]}")
        edges[checked[0]] = checked[1]
    if not errors:
        errors.extend(_graph_errors(edges))
    return errors


def validate_data_model(value: Any, known_events: Collection[str] | None = None) -> list[str]:
    """A data model obeys the string and number rules of the components that bind to it."""
    errors: list[str] = []
    _walk(value, "data", known_events, errors)
    return errors


def validate_surface(
    catalog: Catalog,
    catalog_id: str,
    components: Any,
    data_model: Any = None,
    known_events: Collection[str] | None = None,
    version: str = A2UI_VERSION,
) -> list[str]:
    errors: list[str] = []
    if version != A2UI_VERSION:
        errors.append(f"unsupported A2UI version {version!r}")
    if catalog_id != catalog.catalog_id:
        errors.append(f"unknown catalog {catalog_id!r}")
    errors.extend(validate_components(catalog, components, known_events))
    errors.extend(validate_data_model(data_model, known_events))
    return errors
