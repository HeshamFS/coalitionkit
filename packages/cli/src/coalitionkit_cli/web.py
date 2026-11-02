# SPDX-License-Identifier: Apache-2.0
"""Same-origin room wrapper for static assets and authenticated API routes."""

from pathlib import Path

from starlette.responses import FileResponse
from starlette.staticfiles import StaticFiles
from starlette.types import ASGIApp, Receive, Scope, Send


class Room:
    def __init__(self, server: ASGIApp, dist: Path) -> None:
        self.server = server
        self.dist = dist
        self.static = StaticFiles(directory=dist, html=True)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "")
        reserved = (
            "/v1",
            "/mcp",
            "/admin",
            "/invitations",
            "/cards",
            "/.well-known",
            "/a2a",
            "/healthz",
            "/oauth",
            "/register",
            "/token",
            "/authorize",
        )
        if scope["type"] != "http" or any(
            path == prefix or path.startswith(prefix + "/") for prefix in reserved
        ):
            await self.server(scope, receive, send)
        elif path == "/" or path.startswith(
            ("/confirm/", "/lens", "/gallery", "/join", "/open", "/door", "/signin", "/glasses")
        ):
            await FileResponse(self.dist / "index.html")(scope, receive, send)
        else:
            await self.static(scope, receive, send)
