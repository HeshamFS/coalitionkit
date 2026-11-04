# SPDX-License-Identifier: Apache-2.0
"""Local composition, without a server child process."""

import argparse
import asyncio
import logging
import os
import shutil
import signal
import socket
import subprocess
from contextlib import suppress
from pathlib import Path
from types import FrameType

import uvicorn
from pydantic import SecretStr

from coalitionkit_contracts.resources import checkout_root, resource_path
from coalitionkit_server import Settings, create_server
from coalitionkit_server.app import Server

from .demo import demo_start
from .demo_agents import demo_gateway, demo_runner
from .storage import admin_token, prepare
from .web import Room


def web_dist() -> Path:
    """An installed wheel carries the room's files; a source checkout builds its own."""
    root = checkout_root()
    if root is not None:
        return checkout_web(root / "apps" / "web")
    dist = resource_path("coalitionkit_cli", "web_dist")
    if not (dist / "index.html").is_file():
        raise FileNotFoundError(
            "this install has no web room files. Reinstall coalitionkit, or start with --no-web."
        )
    return dist


def checkout_web(web: Path) -> Path:
    """Serve ``apps/web/dist``, building it when it is absent or older than its source."""
    dist = web / "dist"
    built = (dist / "index.html").is_file()
    if built and not _older_than_source(web, dist):
        return dist
    npm = shutil.which("npm")
    if npm is None:
        if built:
            print("The web room is older than its source; npm was not found to rebuild it.")
            return dist
        raise FileNotFoundError(
            "the web room is not built and npm was not found. "
            "Install Node 22 or newer, or start with --no-web."
        )
    print("Building the web room. It takes a minute or two and only runs when needed.", flush=True)
    steps = [[npm, "run", "build"]]
    if not (web / "node_modules").is_dir():
        steps.insert(0, [npm, "ci", "--no-audit", "--no-fund"])
    for step in steps:
        try:
            subprocess.run(step, cwd=web, check=True)
        except subprocess.CalledProcessError as exc:
            raise OSError(
                f"`npm {' '.join(step[1:])}` failed in {web} (exit {exc.returncode}). "
                "Its output is above. Fix that, or start with --no-web."
            ) from exc
    return dist


def _older_than_source(web: Path, dist: Path) -> bool:
    stamp = (dist / "index.html").stat().st_mtime
    return any(p.stat().st_mtime > stamp for p in (web / "src").rglob("*") if p.is_file())


def run(args: argparse.Namespace) -> int:
    dist = None if args.no_web else web_dist()
    data = prepare(args.data_dir, args.reset)
    saved_port = data / "port"
    port = args.port or (int(saved_port.read_text()) if saved_port.exists() else 0)
    if saved_port.exists() and port != int(saved_port.read_text()):
        raise ValueError("stored host requires the original port; use a new data directory")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", port))
        port = sock.getsockname()[1]
        sock.listen(128)
        saved_port.write_text(str(port), encoding="utf-8")
        base = f"http://127.0.0.1:{port}"
        settings = Settings(
            store=SecretStr(f"sqlite:///{data / 'host.db'}"),
            host_key_file=data / "host.key",
            admin_token=SecretStr(admin_token(data)),
            public_base_url=base,
            bind_host="127.0.0.1",
            bind_port=port,
            genesis="local",
            room_engine="on",
            packs=getattr(args, "pack", []),
        )
        keyed = bool(os.environ.get("COALITIONKIT_META_API_KEY"))
        # Without a key the room still walks end to end, on the built-in rules and fixed checks.
        app = create_server(settings, model_gateway=None if keyed else demo_gateway(live=False))
        # The SDKs turn on INFO logging; this window is for what its owner acts on.
        logging.getLogger().setLevel(logging.WARNING)
        server: Server = app.state.server
        try:
            print(f"Host: {base} | MCP: {base}/mcp", flush=True)
            print(
                "Models: Meta API."
                if keyed
                else "Models: none set, so the room uses built-in rules. "
                "Set COALITIONKIT_META_API_KEY for real ones.",
                flush=True,
            )
            if args.demo:
                demo_start(server, data, args.members, base)
            print(
                "Ctrl+C stops the host. Admin token is in admin.token (not displayed).", flush=True
            )
            print(
                "The API and MCP are on the host address; no web room is served."
                if dist is None
                else f"\nOpen {base}/ and say what needs doing in one sentence.\n",
                flush=True,
            )
        except BaseException:
            server.close()
            raise
        worker = uvicorn.Server(
            uvicorn.Config(
                Room(app, dist) if dist else app,
                host="127.0.0.1",
                port=port,
                access_log=False,
                log_level="warning",
            )
        )

        def stop(signum: int, frame: FrameType | None) -> None:
            worker.should_exit = True

        if os.name == "nt":
            signal.signal(signal.SIGBREAK, stop)

        async def play(coalition: str) -> None:
            try:
                print("Demo: accept each member's charter in the room to begin.", flush=True)
                await demo_runner(server, coalition, getattr(args, "pace", 2)).run()
            except Exception as exc:
                print(f"Demo stopped: {exc}", flush=True)

        async def serve() -> None:
            activity = None
            if args.demo:
                coalition = (data / "demo-coalition").read_text(encoding="utf-8")
                # Existing demos retain their log; never duplicate a partially played script.
                if not server.hosts[coalition].state.tasks:
                    activity = asyncio.create_task(play(coalition))
            try:
                await worker.serve(sockets=[sock])
            finally:
                if activity is not None:
                    activity.cancel()
                    with suppress(asyncio.CancelledError):
                        await activity

        with suppress(KeyboardInterrupt):
            asyncio.run(serve())
    return 0
