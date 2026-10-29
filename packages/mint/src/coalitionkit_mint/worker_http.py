# SPDX-License-Identifier: Apache-2.0
"""Deny HTTP traffic before dispatch, including future methods and transports."""

import hmac
from pathlib import Path

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from .artifact import connect


class ApprovalGate:
    def __init__(self, app: ASGIApp, folder: Path, proof_token: str) -> None:
        self.app = app
        self.folder = folder
        self.proof_token = proof_token

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            discovery = scope["method"] == "GET" and scope["path"] in {
                "/healthz",
                "/.well-known/agent-card.json",
            }
            if not discovery:
                with connect(self.folder) as db:
                    state = db.execute("SELECT state FROM lifecycle").fetchone()[0]
                token = Headers(scope=scope).get("x-mint-proof", "")
                proving = state == "proving" and hmac.compare_digest(token, self.proof_token)
                if state != "approved" and not proving:
                    await JSONResponse({"error": "owner approval required"}, status_code=403)(
                        scope, receive, send
                    )
                    return
        await self.app(scope, receive, send)
