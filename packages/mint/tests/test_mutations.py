# SPDX-License-Identifier: Apache-2.0
"""Mutation tests exercise the production suite through the MCP HTTP boundary."""

import asyncio
import inspect
import socket
from pathlib import Path
from typing import Any

import pytest
import uvicorn
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coalitionkit_mint.artifact import generate
from coalitionkit_mint.process import Sandbox
from coalitionkit_mint.prove import run_suite
from coalitionkit_mint.schema import Attack, Attacks, ResourceConfig, Window
from coalitionkit_mint.templates import resource
from coalitionkit_mint.worker import build


@pytest.mark.parametrize(
    "mutation,failed",
    [
        (None, None),
        ("window", "out of hours"),
        ("overlap", "double booking"),
        ("grid", "slot grid"),
        ("limit", "hold limit"),
        ("refuse", "controls"),
        ("consent", "owners"),
    ],
)
@pytest.mark.parametrize("prerequisites", [[], ["ready"]])
async def test_policy_mutations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str | None,
    failed: str | None,
    prerequisites: list[str],
) -> None:
    source = inspect.getsource(resource.act)
    if mutation == "window":
        source = source.replace(
            "if not any(w.start <= start < end <= w.end for w in config.windows):",
            "if False:",
        )
    if mutation == "overlap":
        source = source.replace(
            '"SELECT 1 FROM bookings WHERE start < ? AND end > ?"',
            '"SELECT 1 FROM bookings WHERE 0 AND start < ? AND end > ?"',
        )
    if mutation == "grid":
        source = source.replace('raise Refusal("off_grid")', "pass")
    if mutation == "limit":
        source = source.replace('raise Refusal("limit reached")', "pass")
    if mutation == "refuse":
        source = source.replace(
            'if tool == "hold_slot":', 'if tool == "hold_slot":\n        raise Refusal("refused")'
        )
    if mutation == "consent":
        from coalitionkit_mint import worker

        def no_consent(*args: Any) -> None:
            pass

        monkeypatch.setattr(worker, "verify_consent", no_consent)
    namespace: dict[str, Any] = dict(vars(resource))
    exec(compile(source, "<policy mutation>", "exec"), namespace)
    monkeypatch.setattr(resource, "act", namespace["act"])
    config = ResourceConfig(
        template="resource",
        name="r",
        windows=[Window(start=540, end=600)],
        duration=30,
        limit=1,
        prerequisites=prerequisites,
    )
    owner = Ed25519PrivateKey.generate()
    folder = tmp_path / "artifact"
    manifest = generate(folder, config, owner.public_key(), "p1")
    sandbox = Sandbox(folder)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sandbox.url = f"http://127.0.0.1:{sock.getsockname()[1]}/mcp"
    app = build(folder, sandbox.token).streamable_http_app(json_response=True)
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", timeout_graceful_shutdown=1))
    task = asyncio.create_task(server.serve(sockets=[sock]))
    try:
        for _ in range(100):
            if server.started:
                break
            await asyncio.sleep(0.01)
        assert server.started
        results = await run_suite(
            sandbox,
            config,
            Attacks(cases=[Attack(tool="write", arguments_json="{}")]),
            owner,
            manifest,
        )
        failures = {r.name for r in results if not r.passed}
        if failed == "controls":
            assert {
                "out of hours",
                "double booking",
                "duration",
                "missing prerequisites",
                "slot grid",
                "hold limit",
                "owner confirm",
                "owner cancel",
            } <= failures
        elif failed == "owners":
            assert {"owner confirm", "owner cancel"} <= failures
        else:
            assert failures == ({failed} if failed else set())
    finally:
        server.should_exit = True
        await asyncio.wait_for(task, 5)
        sock.close()
        sandbox.stop()


async def test_crash_is_not_a_policy_refusal() -> None:
    from typing import cast

    from mcp import Client
    from mcp.shared.exceptions import MCPError

    from coalitionkit_mint.prove import rejected

    class CrashingClient:
        async def call_tool(self, tool: str, arguments: dict[str, Any]) -> Any:
            raise MCPError(-32603, "outside opening rules")

    assert not await rejected(
        cast("Client", CrashingClient()), "hold_slot", {}, "outside opening rules"
    )
