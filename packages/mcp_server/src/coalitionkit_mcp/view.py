# SPDX-License-Identifier: Apache-2.0
"""The one MCP App view, ``ui://coalitionkit/surface-v1.html``.

The page is built from ``apps/web`` (``npm run build:mcp``) into ``assets/surface-v1.html``: one
file, script and style inline, no external request. It holds no Coalition ID; it draws whatever
structured content the host passes it from the tool result and calls tools only through the MCP
Apps bridge. A breaking change ships under a new URI because hosts cache views by URI.
"""

from __future__ import annotations

from functools import cache
from importlib import resources
from typing import Final

from mcp.server.apps import Apps, ResourceCsp

from .tools_read import VIEW_URI

#: Default-deny: no network, no frames, no images, no fonts; only this page's own style and script.
#: The built file carries the same policy in a meta tag; the resource's ``_meta.ui.csp`` names no
#: extra origin, so a host applies its own closed default.
CSP: Final = "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'"

#: Hosts may refuse a view that is too large; the build is checked against this in the web tests.
MAX_VIEW_BYTES: Final = 1_500_000


@cache
def surface_html() -> str:
    """The bundled view. Fails loudly when the build output is missing."""
    asset = resources.files("coalitionkit_mcp").joinpath("assets", "surface-v1.html")
    if not asset.is_file():
        raise RuntimeError(
            "the MCP App view is not built: run `npm --prefix apps/web run build:mcp` first"
        )
    return asset.read_text(encoding="utf-8")


def make_apps() -> Apps:
    """The Apps extension holding the view; ``csp=ResourceCsp()`` declares no extra origins."""
    apps = Apps()
    apps.add_html_resource(
        VIEW_URI,
        surface_html(),
        name="CoalitionKit surface",
        description="The participant's live Coalition surface (version 1).",
        csp=ResourceCsp(),
        prefers_border=True,
    )
    return apps
