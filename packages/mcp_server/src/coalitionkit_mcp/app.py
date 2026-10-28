# SPDX-License-Identifier: Apache-2.0
"""The ASGI app: streamable HTTP MCP inside FastAPI, with the session manager in the lifespan."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager

from fastapi import FastAPI
from mcp.server.transport_security import TransportSecuritySettings

from .access import Deps
from .server import build_server

MCP_PATH = "/mcp"


def create_app(
    deps: Deps,
    *,
    public_url: str,
    issuer_url: str,
    allowed_hosts: Sequence[str] = (),
    allowed_origins: Sequence[str] = (),
) -> FastAPI:
    """Serve the MCP endpoint at ``/mcp``.

    ``public_url`` is the endpoint's own URL. A server reached by a real host name must list that
    name in ``allowed_hosts`` (``host`` or ``host:port``, ``:*`` for any port) and, for browser
    clients, ``allowed_origins``; the SDK refuses any other Host header.
    """
    server = build_server(deps, public_url=public_url, issuer_url=issuer_url)
    mcp_app = server.streamable_http_app(
        streamable_http_path=MCP_PATH,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=list(allowed_hosts),
            allowed_origins=list(allowed_origins),
        ),
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
        # A mounted app's own lifespan never runs, so the host enters the session manager.
        async with server.session_manager.run():
            yield

    app = FastAPI(title="CoalitionKit MCP server", lifespan=lifespan)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:  # pyright: ignore[reportUnusedFunction]
        return {"status": "ok"}

    app.mount("/", mcp_app)
    return app
