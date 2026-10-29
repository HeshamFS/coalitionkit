# SPDX-License-Identifier: Apache-2.0
"""Test support: run an ASGI app under uvicorn on a free localhost port, in a thread.

In-process ASGI transports hang with a2a-sdk 1.3.0, so tests talk to a real socket.
"""

from __future__ import annotations

import socket
import threading
import time

import uvicorn
from starlette.types import ASGIApp


def free_port() -> int:
    """A localhost TCP port nothing is listening on right now."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class RunningServer:
    """``with RunningServer(app, port):`` serves the app until the block ends."""

    def __init__(self, app: ASGIApp, port: int) -> None:
        self.port = port
        self._server = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", lifespan="off")
        )
        self._thread = threading.Thread(target=self._server.run, daemon=True)

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def __enter__(self) -> RunningServer:
        self._thread.start()
        deadline = time.monotonic() + 15
        while not self._server.started:
            if time.monotonic() > deadline or not self._thread.is_alive():
                raise RuntimeError("the test server did not start")
            time.sleep(0.02)
        return self

    def __exit__(self, *exc: object) -> None:
        self._server.should_exit = True
        self._thread.join(timeout=15)
