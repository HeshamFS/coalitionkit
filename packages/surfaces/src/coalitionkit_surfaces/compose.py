# SPDX-License-Identifier: Apache-2.0
"""Compose a surface: validate the tree, or replace it with the fixed fallback layout."""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from typing import Any

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
) -> Composed:
    errors = validate_surface(catalog, catalog.catalog_id, components, data_model, known_events)
    if errors:
        return Composed(fallback_messages(surface_id, catalog.catalog_id), True, errors)
    return Composed(
        [
            create_surface(surface_id, catalog.catalog_id),
            update_components(surface_id, components),
            update_data_model(surface_id, data_model if data_model is not None else {}),
        ],
        False,
        [],
    )
