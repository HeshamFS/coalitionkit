# SPDX-License-Identifier: Apache-2.0
"""Separate loopback MCP process. The owner private key is never present here."""

import argparse
import hmac
import json
import threading
from pathlib import Path
from typing import Any, cast

import uvicorn
from mcp.server.context import CallNext, ServerRequestContext
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse

from coalitionkit_contracts import jwk_to_public_key

from .artifact import connect, load, verify_consent
from .guard import guard
from .schema import DeviceConfig, ResourceConfig
from .templates import device, resource


class Operations:
    def __init__(self, folder: Path) -> None:
        self.folder = folder
        self.config, self.manifest, self.manifest_hash = load(folder)
        self.key = jwk_to_public_key(self.manifest["owner"])

    def invoke(self, tool: str, arguments: dict[str, Any], signature: str = "") -> dict[str, Any]:
        guard(tool, arguments)
        if tool in {"confirm", "cancel"} or (
            tool == "hold_slot"
            and isinstance(self.config, ResourceConfig)
            and self.config.prerequisites
        ):
            verify_consent(self.key, self.manifest_hash, tool, arguments, signature)
        with connect(self.folder) as db:
            db.execute("BEGIN IMMEDIATE")
            if signature:
                db.execute("INSERT INTO consumed_proofs VALUES (?)", (signature,))
            if isinstance(self.config, ResourceConfig):
                return resource.act(db, self.config, tool, arguments)
            return device.act(db, self.config, tool, arguments)


def build(folder: Path, proof_token: str) -> MCPServer:
    ops = Operations(folder)

    async def boundary(ctx: ServerRequestContext[Any, Any], call_next: CallNext) -> Any:
        if ctx.method in {"tools/call", "tools/list"}:
            request = ctx.request
            token = request.headers.get("x-mint-proof", "") if request else ""
            with connect(folder) as db:
                state, signature = db.execute("SELECT state, proof FROM lifecycle").fetchone()
            proving = state == "proving" and hmac.compare_digest(token, proof_token)
            if not proving:
                if state != "approved":
                    raise ValueError("owner approval required")
                verify_consent(ops.key, ops.manifest_hash, "approve", {}, signature)
            if load(folder)[2] != ops.manifest_hash:
                raise ValueError("manifest changed")
            if ctx.method == "tools/call":
                params = ctx.params or {}
                tool = str(params.get("name", ""))
                raw: Any = params.get("arguments", {})
                if not isinstance(raw, dict):
                    raise ValueError("arguments must be an object")
                arguments = cast("dict[str, Any]", raw)
                guard(tool, arguments)
                allowed = {
                    "hold_slot": {"id", "start", "end", "prerequisites", "signature"},
                    "confirm": {"id", "signature"},
                    "cancel": {"id", "signature"},
                }
                if set(arguments) - allowed.get(tool, set()):
                    raise ValueError("unexpected arguments")
                if tool == "hold_slot" and any(
                    type(arguments.get(k)) is not int for k in ("start", "end")
                ):
                    raise ValueError("integer bounds required")
        return await call_next(ctx)

    server = MCPServer("mint", middleware=[boundary])

    def list_free_slots() -> dict[str, Any]:
        return ops.invoke("list_free_slots", {})

    def hold_slot(
        id: str, start: int, end: int, prerequisites: list[str], signature: str = ""
    ) -> dict[str, Any]:
        return ops.invoke(
            "hold_slot",
            {"id": id, "start": start, "end": end, "prerequisites": prerequisites},
            signature,
        )

    def confirm(id: str, signature: str) -> dict[str, Any]:
        return ops.invoke("confirm", {"id": id}, signature)

    def cancel(id: str, signature: str) -> dict[str, Any]:
        return ops.invoke("cancel", {"id": id}, signature)

    def status() -> dict[str, Any]:
        return ops.invoke("status", {})

    def alarm() -> dict[str, Any]:
        return ops.invoke("alarm", {})

    def reader(name: str) -> Any:
        def read() -> dict[str, Any]:
            return ops.invoke(name, {})

        return read

    if isinstance(ops.config, DeviceConfig):
        server.add_tool(status)
        server.add_tool(alarm)
        for field in ops.config.fields:
            server.add_tool(reader("read_" + field.id), name="read_" + field.id)
    else:
        for function in (list_free_slots, hold_slot, confirm, cancel):
            server.add_tool(function)

    @server.custom_route("/healthz", methods=["GET"])
    async def health(_: Request) -> JSONResponse:
        return JSONResponse({"state": "ready"})

    @server.custom_route("/.well-known/agent-card.json", methods=["GET"])
    async def card(_: Request) -> JSONResponse:
        path = folder / "agent-card.json"
        return JSONResponse(
            json.loads(path.read_text()) if path.exists() else {},
            status_code=200 if path.exists() else 404,
        )

    return server


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    # Capability arrives on stdin, never in environment variables or the command line.
    import sys

    proof_token = sys.stdin.readline().strip()
    server = build(Path.cwd(), proof_token)
    app = server.streamable_http_app(
        streamable_http_path="/mcp",
        json_response=True,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=["127.0.0.1:*"],
            allowed_origins=[],
        ),
    )
    runner = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=args.port,
            log_level="error",
            timeout_graceful_shutdown=2,
        )
    )

    def stop_on_eof() -> None:
        sys.stdin.read()
        runner.should_exit = True

    threading.Thread(target=stop_on_eof, daemon=True).start()
    runner.run()


if __name__ == "__main__":
    main()
