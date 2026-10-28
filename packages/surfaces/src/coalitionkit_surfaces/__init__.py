# SPDX-License-Identifier: Apache-2.0
"""Surfaces: AG-UI 1.0 feed and agent sessions and validated A2UI v0.9 trees."""

from .a2ui import (
    A2UI_VERSION,
    ACTIVITY_TYPE,
    CATALOG_ID,
    bound_number,
    create_surface,
    fallback_components,
    fallback_messages,
    update_components,
    update_data_model,
)
from .agent import AgentSession, ConsentError, ConsentRequest, open_requests
from .app import create_app
from .catalog import Catalog, load_catalog, validate_components, validate_surface
from .compose import Composed, compose_surface
from .feed import FeedSession
from .frames import KeepAlive, apply_patch, encode, json_patch
from .hub import SurfaceHub
from .ports import OwnerSigner, ViewerAuth

__all__ = [
    "A2UI_VERSION",
    "ACTIVITY_TYPE",
    "CATALOG_ID",
    "AgentSession",
    "Catalog",
    "Composed",
    "ConsentError",
    "ConsentRequest",
    "FeedSession",
    "KeepAlive",
    "OwnerSigner",
    "SurfaceHub",
    "ViewerAuth",
    "apply_patch",
    "bound_number",
    "compose_surface",
    "create_app",
    "create_surface",
    "encode",
    "fallback_components",
    "fallback_messages",
    "json_patch",
    "load_catalog",
    "open_requests",
    "update_components",
    "update_data_model",
    "validate_components",
    "validate_surface",
]
