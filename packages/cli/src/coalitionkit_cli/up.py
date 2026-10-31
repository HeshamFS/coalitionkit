# SPDX-License-Identifier: Apache-2.0
"""Local composition, without a server child process."""

import argparse
import asyncio
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

from coalitionkit_server import Settings, create_server
from coalitionkit_server.app import Server

from .demo import demo_start
from .demo_agents import demo_gateway, demo_runner
from .storage import admin_token, prepare
from .web import Room


def web_dist() -> Path | None:
    root = Path(__file__).resolve().parents[4]
    web = root / "apps" / "web"
    dist = web / "dist"
    if (dist / "index.html").is_file():
        return dist
    npm = shutil.which("npm")
    if npm is None or not web.is_dir():
        print("Room unavailable: install Node/npm, run npm --prefix apps/web ci, then rerun up.")
        return None
    if not (web / "node_modules").is_dir():
        print("Installing web dependencies: npm --prefix apps/web ci", flush=True)
        if build_command(npm, web, ["ci"]):
            print("Web dependencies could not be installed; host still available.")
            return None
    print("Building the web room: npm --prefix apps/web run build", flush=True)
    code = build_command(npm, web, ["run", "build"])
    if code or not (dist / "index.html").is_file():
        print("Room build failed: run npm --prefix apps/web ci and rerun up; host still available.")
        return None
    return dist


def build_command(npm: str, web: Path, arguments: list[str]) -> int:
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    child = subprocess.Popen(
        [npm, "--prefix", str(web), *arguments],
        creationflags=flags,
        start_new_session=os.name != "nt",
    )
    try:
        return child.wait()
    except KeyboardInterrupt:
        if os.name == "nt":
            child.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            os.killpg(child.pid, signal.SIGINT)
        try:
            child.wait(timeout=15)
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(child.pid), "/T", "/F"],
                    check=False,
                    capture_output=True,
                    creationflags=flags,
                )
            else:
                os.killpg(child.pid, signal.SIGKILL)
            child.wait()
        raise


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
        )
        app = create_server(
            settings,
            model_gateway=(
                demo_gateway(live=bool(os.environ.get("COALITIONKIT_META_API_KEY")))
                if args.demo
                else None
            ),
        )
        server: Server = app.state.server
        try:
            mode = (
                "Meta API configured"
                if os.environ.get("COALITIONKIT_META_API_KEY")
                else "scripted demo (no model key required)"
                if args.demo
                else "no model key configured"
            )
            print(f"Mode: {mode}", flush=True)
            print(f"Host: {base} | MCP: {base}/mcp", flush=True)
            code = server.registry.issue_start()
            print(f"Start a coalition: {base}/#start={code}", flush=True)
            if args.demo:
                demo_start(server, data, args.members, base)
            if dist is None:
                print(
                    "No room served. Use viewer tokens as Bearer credentials for the API.",
                    flush=True,
                )
            else:
                print(f"Open {base}/ and paste a Viewer token, then select Continue.", flush=True)
            print(
                "Ctrl+C stops the host. Admin token is in admin.token (not displayed).", flush=True
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
