# SPDX-License-Identifier: Apache-2.0
"""Compose a surface: validate the tree, or replace it with the fixed fallback layout."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, cast

from .a2ui import create_surface, fallback_messages, update_components, update_data_model
from .catalog import Catalog, validate_surface

Document = dict[str, Any]


@dataclass(frozen=True)
class Composed:
    """A surface's three messages (``createSurface`` first) and whether they are the fallback."""

    messages: list[Document]
    fallback: bool
    errors: list[str]


def compose_surface(
    catalog: Catalog,
    surface_id: str,
    components: list[Document],
    data_model: Any = None,
    known_events: Collection[str] | None = None,
    *,
    views: Mapping[str, Mapping[str, tuple[str, ...]]] | None = None,
    roles: Collection[str] = (),
    device: str = "wide",
) -> Composed:
    order = list(
        dict.fromkeys(
            name for role in roles for name in (views or {}).get(role, {}).get(device, ())
        )
    )
    unknown = [
        name
        for devices in (views or {}).values()
        for names in devices.values()
        for name in names
        if name not in catalog.components
    ]
    if unknown:
        return Composed(
            fallback_messages(surface_id, catalog.catalog_id),
            True,
            [f"unknown pack view component {name}" for name in unknown],
        )
    errors = validate_surface(catalog, catalog.catalog_id, components, data_model, known_events)
    if errors:
        return Composed(fallback_messages(surface_id, catalog.catalog_id), True, errors)
    if order:
        components = deepcopy(components)
        rank = {name: index for index, name in enumerate(order)}
        by_id = {node.get("id"): node for node in components}
        for node in components:
            spec = catalog.components.get(node.get("component", ""))
            if spec is not None:
                for prop in spec.links:
                    children = node.get(prop)
                    if isinstance(children, list) and all(
                        isinstance(c, str) for c in cast(list[Any], children)
                    ):
                        node[prop] = sorted(
                            cast(list[str], children),
                            key=lambda child: rank.get(
                                by_id.get(child, {}).get("component", ""), len(rank)
                            ),
                        )
        components.sort(
            key=lambda node: (
                -1 if node.get("id") == "root" else rank.get(node.get("component", ""), len(rank))
            )
        )
    return Composed(
        [
            create_surface(surface_id, catalog.catalog_id),
            update_components(surface_id, components),
            update_data_model(surface_id, data_model if data_model is not None else {}),
        ],
        False,
        [],
    )
