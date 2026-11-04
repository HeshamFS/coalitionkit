# SPDX-License-Identifier: Apache-2.0
from typing import Any

from coalitionkit_surfaces.catalog import Catalog, ComponentSpec, PropSpec
from coalitionkit_surfaces.compose import compose_surface


def test_pack_order_controls_child_references_and_refuses_unknown() -> None:
    catalog = Catalog(
        "test",
        {
            "List": ComponentSpec({"children": PropSpec("children")}),
            "Card": ComponentSpec({}),
            "Extra": ComponentSpec({}),
        },
    )
    nodes: list[dict[str, Any]] = [
        {"id": "root", "component": "List", "children": ["a", "b"]},
        {"id": "a", "component": "Card"},
        {"id": "b", "component": "Extra"},
    ]
    views = {"helper": {"wide": ("Extra", "Card"), "compact": ("Card", "Extra")}}
    wide = compose_surface(catalog, "test", nodes, views=views, roles=["helper"])
    assert not wide.fallback
    assert wide.messages[1]["updateComponents"]["components"][0]["children"] == ["b", "a"]
    compact = compose_surface(
        catalog, "test", nodes, views=views, roles=["helper"], device="compact"
    )
    assert compact.messages[1]["updateComponents"]["components"][0]["children"] == ["a", "b"]
    assert nodes[0]["children"] == ["a", "b"]
    bad = compose_surface(catalog, "test", nodes, views={"helper": {"wide": ("Script",)}})
    assert bad.fallback and "Script" in bad.errors[0]
