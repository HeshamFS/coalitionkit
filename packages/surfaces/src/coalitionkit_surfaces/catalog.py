# SPDX-License-Identifier: Apache-2.0
"""The closed component catalog and the validator every A2UI tree passes before it is sent."""

from __future__ import annotations

import json
import re
from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime
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


PROP_TYPES = frozenset(
    {
        "string",
        "number",
        "integer",
        "boolean",
        "datetime",
        "id",
        "enum",
        "binding",
        "subject",
        "scope",
        "child",
        "children",
        "array",
        "object",
        "any",
    }
)
LINK_TYPES = frozenset({"child", "children"})


@dataclass(frozen=True)
class PropSpec:
    type: str
    required: bool = False
    values: frozenset[str] = frozenset()
    items: dict[str, PropSpec] | None = None  # for arrays of records: the fields each may carry


@dataclass(frozen=True)
class ComponentSpec:
    types: dict[str, PropSpec]

    @property
    def props(self) -> frozenset[str]:
        return frozenset(self.types)

    @property
    def required(self) -> frozenset[str]:
        return frozenset(name for name, spec in self.types.items() if spec.required)

    @property
    def links(self) -> frozenset[str]:
        return frozenset(name for name, spec in self.types.items() if spec.type in LINK_TYPES)


@dataclass(frozen=True)
class Catalog:
    catalog_id: str
    components: dict[str, ComponentSpec]


def load_catalog(path: str | Path) -> Catalog:
    """Read the typed catalog: ``{catalogId, components: {Name: {props: {p: {type, ...}}}}}``.

    Every prop has a ``type`` from ``PROP_TYPES``, an optional ``required`` flag and, for
    ``enum``, its ``values``. Props of type ``child`` and ``children`` hold component ids.
    """
    data = _as_doc(json.loads(Path(path).read_text(encoding="utf-8")))
    specs = _as_doc(data.get("components")) if data is not None else None
    if data is None or specs is None:
        raise ValueError("catalog file needs a components object")
    catalog_id = data.get("catalogId", CATALOG_ID)
    if not isinstance(catalog_id, str) or not catalog_id:
        raise ValueError("catalogId must be a string")
    components = {name: _component(name, spec) for name, spec in specs.items()}
    return Catalog(catalog_id, components)


def _component(name: str, spec: Any) -> ComponentSpec:
    body = _as_doc(spec)
    props = _as_doc(body.get("props", {})) if body is not None else None
    if body is None or props is None:
        raise ValueError(f"component {name} needs a props object")
    return ComponentSpec(_props(name, props))


def _props(name: str, props: Document) -> dict[str, PropSpec]:
    types: dict[str, PropSpec] = {}
    for prop, raw in props.items():
        item = _as_doc(raw)
        kind = item.get("type") if item is not None else None
        if item is None or kind not in PROP_TYPES:
            raise ValueError(f"component {name} prop {prop}: unknown type {kind!r}")
        values = frozenset(str(v) for v in cast(list[Any], item.get("values", [])))
        if kind == "enum" and not values:
            raise ValueError(f"component {name} prop {prop}: enum needs values")
        record = _as_doc(item.get("items"))
        fields = _as_doc(record.get("props")) if record is not None else None
        if record is not None and (kind != "array" or fields is None):
            raise ValueError(f"component {name} prop {prop}: items need an array of props")
        nested = _props(f"{name}.{prop}", fields) if fields is not None else None
        types[str(prop)] = PropSpec(str(kind), bool(item.get("required", False)), values, nested)
    return types


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
    elif _is_subject(value):
        # A revisioned subject anywhere in a tree or data model: the revision is protocol data.
        _walk({"kind": value["kind"], "id": value["id"]}, where, known, errors)
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
    for door in sorted(spec.links & set(node)):
        value = node[door]
        if spec.types[door].type == "children" and not isinstance(value, list):
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
        if prop in spec.types and prop not in spec.links:
            _check_prop(spec.types[prop], value, f"{where}.{prop}", known, errors)
    return ident, links


def _is_binding(value: Any) -> bool:
    body = _as_doc(value)
    return body is not None and set(body) == {"path"} and _is_path(body["path"])


def _is_path(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("/") and not _HTML.search(value)


def _is_datetime(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _is_subject(value: Any) -> bool:
    body = _as_doc(value)
    if body is None or set(body) != {"kind", "id", "revision"}:
        return False
    revision = body["revision"]
    return (
        isinstance(body["kind"], str)
        and isinstance(body["id"], str)
        and isinstance(revision, int)
        and not isinstance(revision, bool)
        and revision >= 1
    )


def _is_scope(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value)
    body = _as_doc(value)
    if (
        body is None
        or not isinstance(body.get("audience"), str)
        or not set(body) <= {"audience", "redact"}
    ):
        return False
    redact = body.get("redact", [])
    return isinstance(redact, list) and all(isinstance(x, str) for x in cast(list[Any], redact))


def _shape_ok(spec: PropSpec, value: Any) -> bool:
    match spec.type:
        case "string":
            return isinstance(value, str)
        case "enum":
            return isinstance(value, str) and value in spec.values
        case "boolean":
            return isinstance(value, bool)
        case "datetime":
            return _is_datetime(value)
        case "id":
            return isinstance(value, str) and bool(_ID.fullmatch(value))
        case "number":
            return _is_bound(value)
        case "integer":
            return _is_bound(value) and isinstance(value["value"], int)
        case "subject":
            return _is_subject(value)
        case "scope":
            return _is_scope(value)
        case "array":
            return isinstance(value, list)
        case "object":
            return isinstance(value, dict)
        case "binding":
            return False  # a binding prop takes only {path}, which returns before this check
        case _:
            return True  # any


def _check_prop(
    spec: PropSpec, value: Any, where: str, known: Collection[str] | None, errors: list[str]
) -> None:
    """A prop is either a data binding ``{path}`` or a literal of its declared type."""
    if _is_binding(value):
        return
    looks_numeric = _is_number(value) or frozenset(_as_doc(value) or {}) == _BOUND_KEYS
    if spec.type in {"number", "integer"} and looks_numeric:
        _walk(value, where, known, errors)  # reports unbound or malformed numbers in its own words
        return
    if not _shape_ok(spec, value):
        errors.append(f"{where}: expected {spec.type}")
        return
    if spec.type == "subject":
        # The revision is protocol data, not a displayed number; only its strings are walked.
        _walk({"kind": value["kind"], "id": value["id"]}, where, known, errors)
        return
    if spec.items is not None:
        _check_records(spec.items, cast(list[Any], value), where, known, errors)
        return
    _walk(value, where, known, errors)


def _check_records(
    fields: dict[str, PropSpec],
    records: list[Any],
    where: str,
    known: Collection[str] | None,
    errors: list[str],
) -> None:
    for index, record in enumerate(records):
        body = _as_doc(record)
        if body is None:
            errors.append(f"{where}[{index}]: expected a record")
            continue
        for key in sorted(set(body) - set(fields)):
            errors.append(f"{where}[{index}]: field {key} not allowed")
        for key in sorted(name for name, f in fields.items() if f.required and name not in body):
            errors.append(f"{where}[{index}]: missing required field {key}")
        for key, item in body.items():
            if key in fields:
                _check_prop(fields[key], item, f"{where}[{index}].{key}", known, errors)


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
    if not errors and data_model is not None:
        errors.extend(_bound_type_errors(catalog, components, data_model, known_events))
    return errors


_MISSING = object()


def _resolve(data: Any, path: str) -> Any:
    current: Any = data
    for raw in path.split("/")[1:]:
        key = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            items = cast(list[Any], current)
            if not (key.isdigit() and int(key) < len(items)):
                return _MISSING
            current = items[int(key)]
        elif (mapping := _as_doc(current)) is not None and key in mapping:
            current = mapping[key]
        elif key != "":
            return _MISSING
    return current


def _bound_type_errors(
    catalog: Catalog, components: list[Any], data: Any, known: Collection[str] | None
) -> list[str]:
    """A prop bound to the data model must find a value of its declared type there."""
    errors: list[str] = []
    for node in components:
        item = cast(Document, node)
        spec = catalog.components[str(item["component"])]
        for prop, value in item.items():
            prop_spec = spec.types.get(prop)
            if prop_spec is None or prop in spec.links or not _is_binding(value):
                continue
            if prop_spec.type in {"binding", "any"}:
                continue
            resolved = _resolve(data, value["path"])
            if resolved is not _MISSING:
                where = f"component {item['id']}.{prop} -> {value['path']}"
                _check_prop(prop_spec, resolved, where, known, errors)
    return errors
