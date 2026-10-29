# SPDX-License-Identifier: Apache-2.0
"""A2UI v0.9 message builders and the fixed fallback layout."""

from __future__ import annotations

from typing import Any

Document = dict[str, Any]

A2UI_VERSION = "v0.9"
CATALOG_ID = "coalitionkit/v0_9"
ROOT_ID = "root"
ACTIVITY_TYPE = "a2ui-surface"


def create_surface(
    surface_id: str, catalog_id: str = CATALOG_ID, theme: Document | None = None
) -> Document:
    body: Document = {"surfaceId": surface_id, "catalogId": catalog_id}
    if theme is not None:
        body["theme"] = theme
    return {"version": A2UI_VERSION, "createSurface": body}


def update_components(surface_id: str, components: list[Document]) -> Document:
    return {
        "version": A2UI_VERSION,
        "updateComponents": {"surfaceId": surface_id, "components": components},
    }


def update_data_model(surface_id: str, value: Any, path: str = "/") -> Document:
    return {
        "version": A2UI_VERSION,
        "updateDataModel": {"surfaceId": surface_id, "path": path, "value": value},
    }


def bound_number(value: int | float, event_ref: str) -> Document:
    """A number tied to the event it came from: the only form of a number the catalog accepts."""
    return {"value": value, "event_ref": event_ref}


def fallback_components() -> list[Document]:
    """The fixed layout shown when a composed tree fails validation."""
    return [
        {
            "id": ROOT_ID,
            "component": "Card",
            "title": "Standard view",
            "fields": {"path": "/fields"},
        }
    ]


def fallback_messages(surface_id: str, catalog_id: str = CATALOG_ID) -> list[Document]:
    return [
        create_surface(surface_id, catalog_id),
        update_components(surface_id, fallback_components()),
        update_data_model(surface_id, {"fields": []}),
    ]
