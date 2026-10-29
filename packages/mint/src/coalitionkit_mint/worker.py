# SPDX-License-Identifier: Apache-2.0
"""Separate loopback MCP process. The owner private key is never present here."""

import argparse
import hmac
import json
import os
import socket
import threading
from pathlib import Path
from typing import Any, cast

import uvicorn
from mcp.server.context import CallNext, ServerRequestContext
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from mcp.shared.exceptions import MCPError
from starlette.requests import Request
from starlette.responses import JSONResponse

from coalitionkit_contracts import SignatureError, jwk_to_public_key

from .artifact import connect, load, verify_consent
from .guard import guard
from .refusal import Refusal
from .schema import DeviceConfig, ResourceConfig
from .templates import device, resource
from .worker_http import ApprovalGate


class Operations:
    def __init__(self, folder: Path) -> None:
        self.folder = folder
        self.config, self.manifest, self.manifest_hash = load(folder)
        self.key = jwk_to_public_key(self.manifest["owner"])

    def invoke(self, tool: str, arguments: dict[str, Any], signature: str = "") -> dict[str, Any]:
        guard(tool, arguments)
        with connect(self.folder) as db:
            db.execute("BEGIN IMMEDIATE")
            requires_proof = tool in {"confirm", "cancel"} or (
                tool == "hold_slot"
                and isinstance(self.config, ResourceConfig)
                and bool(self.config.prerequisites)
            )
            if tool in {"confirm", "cancel"}:
                row = db.execute(
                    "SELECT id, start, end, nonce, revision FROM bookings WHERE id=?",
                    (arguments.get("id"),),
                ).fetchone()
                if row is None or arguments != dict(
                    zip(("id", "start", "end", "nonce", "revision"), row, strict=True)
                ):
                    raise Refusal("stale_hold")
            if requires_proof:
                verify_consent(self.key, self.manifest_hash, tool, arguments, signature)
                if tool in {"confirm", "cancel"}:
                    db.execute("INSERT INTO consumed_proofs VALUES (?)", (signature,))
            if isinstance(self.config, ResourceConfig):
                return resource.act(db, self.config, tool, arguments)
            return device.act(db, self.config, tool, arguments)

    def call(self, tool: str, arguments: dict[str, Any], signature: str = "") -> dict[str, Any]:
        try:
            return self.invoke(tool, arguments, signature)
        except Refusal as exc:
            raise MCPError(-32001, str(exc)) from exc
        except SignatureError as exc:
            raise MCPError(-32001, "owner_consent") from exc


def build(folder: Path, proof_token: str) -> MCPServer:
    ops = Operations(folder)

    async def check_request(ctx: ServerRequestContext[Any, Any], call_next: CallNext) -> Any:
        request = ctx.request
        token = request.headers.get("x-mint-proof", "") if request else ""
        with connect(folder) as db:
            state, signature = db.execute("SELECT state, proof FROM lifecycle").fetchone()
        proving = state == "proving" and hmac.compare_digest(token, proof_token)
        if not proving:
            if state != "approved":
                raise Refusal("owner approval required")
            verify_consent(ops.key, ops.manifest_hash, "approve", {}, signature)
        if load(folder)[2] != ops.manifest_hash:
            raise Refusal("manifest changed")
        if ctx.method == "tools/call":
            params = ctx.params or {}
            tool = str(params.get("name", ""))
            raw: Any = params.get("arguments", {})
            if not isinstance(raw, dict):
                raise Refusal("arguments must be an object")
            arguments = cast("dict[str, Any]", raw)
            guard(tool, arguments)
            allowed = {
                "hold_slot": {"start", "end", "prerequisites", "signature"},
                "confirm": {"id", "start", "end", "nonce", "revision", "signature"},
                "cancel": {"id", "start", "end", "nonce", "revision", "signature"},
            }
            if set(arguments) - allowed.get(tool, set()):
                raise Refusal("unexpected arguments")
            if tool == "hold_slot" and any(
                type(arguments.get(k)) is not int for k in ("start", "end")
            ):
                raise Refusal("integer bounds required")
        return await call_next(ctx)

    async def boundary(ctx: ServerRequestContext[Any, Any], call_next: CallNext) -> Any:
        try:
            return await check_request(ctx, call_next)
        except Refusal as exc:
            raise MCPError(-32001, str(exc)) from exc

    server = MCPServer("mint", middleware=[boundary])

    def list_free_slots() -> dict[str, Any]:
        return ops.call("list_free_slots", {})

    def hold_slot(
        start: int, end: int, prerequisites: list[str], signature: str = ""
    ) -> dict[str, Any]:
        return ops.call(
            "hold_slot",
            {"start": start, "end": end, "prerequisites": prerequisites},
            signature,
        )

    def confirm(
        id: str, start: int, end: int, nonce: str, revision: int, signature: str
    ) -> dict[str, Any]:
        return ops.call(
            "confirm",
            {"id": id, "start": start, "end": end, "nonce": nonce, "revision": revision},
            signature,
        )

    def cancel(
        id: str, start: int, end: int, nonce: str, revision: int, signature: str
    ) -> dict[str, Any]:
        return ops.call(
            "cancel",
            {"id": id, "start": start, "end": end, "nonce": nonce, "revision": revision},
            signature,
        )

    def status() -> dict[str, Any]:
        return ops.call("status", {})

    def alarm() -> dict[str, Any]:
        return ops.call("alarm", {})

    def reader(name: str) -> Any:
        def read() -> dict[str, Any]:
            return ops.call(name, {})

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
    app.add_middleware(ApprovalGate, folder=Path.cwd(), proof_token=proof_token)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1], flush=True)
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
        threading.Timer(3, lambda: os._exit(0)).start()

    threading.Thread(target=stop_on_eof, daemon=True).start()
    runner.run(sockets=[sock])


if __name__ == "__main__":
    main()
