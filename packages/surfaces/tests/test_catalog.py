# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import itertools
import json
from pathlib import Path
from typing import Any

import pytest
from surfaces_support import FIXTURE

from coalitionkit_surfaces import (
    CATALOG_ID,
    bound_number,
    compose_surface,
    fallback_components,
    fallback_messages,
    load_catalog,
    validate_components,
    validate_surface,
)
from coalitionkit_surfaces.catalog import MAX_COMPONENTS, MAX_DEPTH, Catalog

Tree = list[dict[str, Any]]


@pytest.fixture
def catalog() -> Catalog:
    return load_catalog(FIXTURE)


def card(ident: str, *children: str, **extra: Any) -> dict[str, Any]:
    node: dict[str, Any] = {"id": ident, "component": "Card", "title": ident, **extra}
    if children:
        node["child"] = children[0]
    return node


def column(ident: str, *children: str) -> dict[str, Any]:
    return {"id": ident, "component": "List", "children": list(children)}


GOOD: Tree = [column("root", "a", "b"), card("a"), card("b")]


def errors(catalog: Catalog, tree: Tree) -> list[str]:
    return validate_components(catalog, tree)


def test_good_tree_passes(catalog: Catalog) -> None:
    assert errors(catalog, GOOD) == []
    assert validate_surface(catalog, CATALOG_ID, GOOD, {"fields": []}) == []


def test_fallback_layout_is_valid_in_the_catalog(catalog: Catalog) -> None:
    assert errors(catalog, fallback_components()) == []


def test_unknown_component_rejected(catalog: Catalog) -> None:
    bad = [{"id": "root", "component": "Script", "src": "x"}]
    assert any("unknown component" in e for e in errors(catalog, bad))


def test_unknown_prop_and_missing_required_prop_rejected(catalog: Catalog) -> None:
    assert any("not allowed" in e for e in errors(catalog, [card("root", onclick="x")]))
    missing = [{"id": "root", "component": "Card"}]
    assert any("missing required" in e for e in errors(catalog, missing))


def test_unknown_catalog_id_and_version_rejected(catalog: Catalog) -> None:
    assert any("unknown catalog" in e for e in validate_surface(catalog, "other/v1", GOOD))
    assert any("version" in e for e in validate_surface(catalog, CATALOG_ID, GOOD, version="v1.0"))


def test_more_than_one_root_rejected(catalog: Catalog) -> None:
    tree = [column("root", "a"), card("a"), card("b")]
    assert any("more than one root" in e for e in errors(catalog, tree))


def test_missing_root_rejected(catalog: Catalog) -> None:
    assert any("no component with id root" in e for e in errors(catalog, [card("main")]))


def test_orphan_rejected(catalog: Catalog) -> None:
    tree = [column("root", "a"), card("a"), card("x", "y"), card("y", "x")]
    found = errors(catalog, tree)
    assert any("orphan component x" in e for e in found)


def test_cycle_rejected(catalog: Catalog) -> None:
    tree = [column("root", "a"), card("a", "b"), card("b", "a")]
    assert any("cycle" in e for e in errors(catalog, tree))


def test_dangling_reference_rejected(catalog: Catalog) -> None:
    assert any("missing component" in e for e in errors(catalog, [column("root", "ghost")]))


def test_duplicate_ids_rejected(catalog: Catalog) -> None:
    tree = [column("root", "a"), card("a"), card("a")]
    assert any("duplicate id" in e for e in errors(catalog, tree))


def test_more_than_500_components_rejected(catalog: Catalog) -> None:
    names = [f"n{i}" for i in range(MAX_COMPONENTS)]
    tree = [column("root", *names), *[card(n) for n in names]]
    assert len(tree) == MAX_COMPONENTS + 1
    assert any("over 500" in e for e in errors(catalog, tree))
    exactly = [column("root", *names[:-1]), *[card(n) for n in names[:-1]]]
    assert len(exactly) == MAX_COMPONENTS
    assert errors(catalog, exactly) == []


def chain(length: int) -> Tree:
    ids = ["root", *[f"n{i}" for i in range(1, length)]]
    tree = [card(i, nxt) for i, nxt in itertools.pairwise(ids)]
    return [*tree, card(ids[-1])]


def test_depth_over_24_rejected(catalog: Catalog) -> None:
    assert errors(catalog, chain(MAX_DEPTH)) == []
    assert any("depth" in e for e in errors(catalog, chain(MAX_DEPTH + 1)))


@pytest.mark.parametrize(
    "text",
    [
        "<script>alert(1)</script>",
        "x <b>bold</b>",
        "<img src=x onerror=1>",
        "&lt;b&gt;",
        "&#60;b",
        "<!-- c -->",
    ],
)
def test_html_in_string_props_rejected(catalog: Catalog, text: str) -> None:
    assert any("html" in e for e in errors(catalog, [card("root", status=text)]))
    nested = card("root", fields=[{"label": text}])
    assert any("html" in e for e in errors(catalog, [nested]))


def test_plain_text_with_a_comparison_is_allowed(catalog: Catalog) -> None:
    assert errors(catalog, [card("root", status="3 < 4 and fine")]) == []


def test_unbound_numbers_rejected_everywhere(catalog: Catalog) -> None:
    gauge = {"id": "root", "component": "Gauge", "value": 7}
    assert any("not bound" in e for e in errors(catalog, [gauge]))
    nested = card("root", fields=[{"label": "n", "value": 2.5}])
    assert any("not bound" in e for e in errors(catalog, [nested]))
    assert any("not bound" in e for e in validate_surface(catalog, CATALOG_ID, GOOD, {"n": 1}))


def test_bound_numbers_pass_and_check_their_event(catalog: Catalog) -> None:
    gauge = {"id": "root", "component": "Gauge", "value": bound_number(7, "evt1"), "unit": "h"}
    assert errors(catalog, [gauge]) == []
    assert validate_components(catalog, [gauge], {"evt1"}) == []
    assert any("unknown event" in e for e in validate_components(catalog, [gauge], {"evt2"}))
    wrong = {"id": "root", "component": "Gauge", "value": {"value": True, "event_ref": "e"}}
    assert errors(catalog, [wrong])


def test_invalid_surface_is_replaced_by_the_fixed_fallback(catalog: Catalog) -> None:
    bad = [{"id": "root", "component": "Script"}]
    composed = compose_surface(catalog, "main", bad, {"fields": []})
    assert composed.fallback and composed.errors
    assert composed.messages == fallback_messages("main")
    good = compose_surface(catalog, "main", GOOD, {"fields": []})
    assert not good.fallback and good.errors == []
    assert [next(iter(set(m) - {"version"})) for m in good.messages] == [
        "createSurface",
        "updateComponents",
        "updateDataModel",
    ]
    assert all(m["version"] == "v0.9" for m in good.messages)
    assert good.messages[0]["createSurface"]["catalogId"] == "coalitionkit/v0_9"


def test_loader_reads_any_path_and_rejects_bad_files(tmp_path: Path) -> None:
    path = tmp_path / "c.json"
    path.write_text(json.dumps({"catalog_id": "x/v1", "components": {"A": {"props": ["p"]}}}))
    loaded = load_catalog(path)
    assert loaded.catalog_id == "x/v1" and "A" in loaded.components
    path.write_text(json.dumps({"components": {"A": {"props": [], "required": ["q"]}}}))
    with pytest.raises(ValueError, match="requires props"):
        load_catalog(path)
    path.write_text("{}")
    with pytest.raises(ValueError, match="components"):
        load_catalog(path)
