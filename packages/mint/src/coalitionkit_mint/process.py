# SPDX-License-Identifier: Apache-2.0
"""Loopback process ownership and MCP client connections."""

import asyncio
import atexit
import os
import secrets
import signal
import subprocess
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client


def scrub_environment() -> dict[str, str]:
    # An allowlist also removes unknown provider credentials and Python startup hooks.
    allowed = {"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "LANG", "LC_ALL"}
    return {k: v for k, v in os.environ.items() if k.upper() in allowed}


class Sandbox:
    def __init__(self, folder: Path) -> None:
        self.folder = folder.resolve()
        self.token = secrets.token_urlsafe(32)
        self.port = 0
        self.url = ""
        self.process: subprocess.Popen[str] | None = None
        atexit.register(self.stop)
        self.log = (self.folder / "worker.log").open("w", encoding="utf-8")

    async def start(self) -> None:
        self.process = subprocess.Popen(
            [sys.executable, "-I", "-m", "coalitionkit_mint.worker", "--port", str(self.port)],
            cwd=self.folder,
            env=scrub_environment(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.log,
            text=True,
            start_new_session=os.name != "nt",
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        assert self.process.stdin is not None
        self.process.stdin.write(self.token + "\n")
        self.process.stdin.flush()
        assert self.process.stdout is not None
        try:
            line = await asyncio.wait_for(asyncio.to_thread(self.process.stdout.readline), 30)
            self.port = int(line.strip())
            self.url = f"http://127.0.0.1:{self.port}/mcp"
        except BaseException:
            self.stop()
            raise
        async with httpx2.AsyncClient(trust_env=False, timeout=1) as http:
            for _ in range(150):
                if self.process.poll() is not None:
                    raise RuntimeError("Mint worker exited; inspect worker.log")
                try:
                    response = await http.get(self.url.replace("/mcp", "/healthz"))
                    if response.status_code == 200:
                        return
                except httpx2.TransportError:
                    pass
                await asyncio.sleep(0.05)
        raise TimeoutError("Mint worker startup")

    @asynccontextmanager
    async def client(self, *, proving: bool = False) -> AsyncGenerator[Client]:
        headers = {"x-mint-proof": self.token} if proving else {}
        async with (
            httpx2.AsyncClient(headers=headers, trust_env=False) as http,
            Client(streamable_http_client(self.url, http_client=http)) as client,
        ):
            yield client

    def stop(self) -> None:
        try:
            if self.process is not None:
                if self.process.stdin is not None and not self.process.stdin.closed:
                    self.process.stdin.close()
                try:
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    if os.name == "nt":
                        subprocess.run(
                            ["taskkill", "/PID", str(self.process.pid), "/T", "/F"],
                            capture_output=True,
                            check=False,
                            creationflags=subprocess.CREATE_NO_WINDOW,
                        )
                    else:
                        os.killpg(self.process.pid, signal.SIGKILL)
                    self.process.kill()
                    self.process.wait(timeout=5)
                if self.process.stdout is not None:
                    self.process.stdout.close()
        finally:
            self.log.close()
            atexit.unregister(self.stop)
