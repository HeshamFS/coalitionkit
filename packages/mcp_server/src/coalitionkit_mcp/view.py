# SPDX-License-Identifier: Apache-2.0
"""The one MCP App view, ``ui://coalitionkit/surface-v1.html``: a small placeholder page.

A breaking change ships under a new URI because hosts cache views by URI. The page holds no
Coalition ID: it shows whatever structured content the host passes it from the tool result.
"""

from __future__ import annotations

from typing import Final

from mcp.server.apps import Apps, ResourceCsp

from .tools_read import VIEW_URI

#: Default-deny: no network, no frames, no images, no fonts; only this page's own style and script.
CSP: Final = "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'"

SURFACE_HTML: Final = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="{CSP}">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CoalitionKit</title>
<style>
  body {{ font: 16px/1.5 system-ui, sans-serif; margin: 16px; color: CanvasText; }}
  pre {{ white-space: pre-wrap; }}
</style>
</head>
<body>
<h1>CoalitionKit</h1>
<p id="state">Waiting for your Coalition.</p>
<pre id="data"></pre>
<script>
  window.addEventListener("message", function (event) {{
    var msg = event.data;
    if (!msg || msg.method !== "ui/notifications/tool-result") return;
    var result = (msg.params || {{}}).structuredContent || {{}};
    document.getElementById("state").textContent = "Your Coalition surface (placeholder view).";
    document.getElementById("data").textContent = JSON.stringify(result, null, 2);
  }});
</script>
</body>
</html>
"""


def make_apps() -> Apps:
    """The Apps extension holding the view; ``csp=ResourceCsp()`` declares no extra origins."""
    apps = Apps()
    apps.add_html_resource(
        VIEW_URI,
        SURFACE_HTML,
        name="CoalitionKit surface",
        description="The participant's live Coalition surface (version 1).",
        csp=ResourceCsp(),
    )
    return apps
