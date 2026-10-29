# SPDX-License-Identifier: Apache-2.0
"""Real process shutdown and kernel-assigned port regression tests."""

import asyncio
import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coalitionkit_mint.artifact import generate
from coalitionkit_mint.process import Sandbox
from coalitionkit_mint.schema import ResourceConfig


@pytest.mark.parametrize("config", ["resource"], indirect=True)
async def test_worker_chooses_port(tmp_path: Path, config: dict[str, Any]) -> None:
    folder = tmp_path / "artifact"
    generate(
        folder,
        ResourceConfig.model_validate(config),
        Ed25519PrivateKey.generate().public_key(),
        "p1",
    )
    sandbox = Sandbox(folder)
    assert sandbox.port == 0
    try:
        await sandbox.start()
        assert sandbox.port > 0
        with socket.create_connection(("127.0.0.1", sandbox.port), 1):
            pass
    finally:
        sandbox.stop()


def test_stop_kills_unresponsive_tree(tmp_path: Path) -> None:
    sandbox = Sandbox(tmp_path)
    sandbox.process = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sandbox.log,
        text=True,
        start_new_session=os.name != "nt",
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    started = time.monotonic()
    try:
        sandbox.stop()
        assert sandbox.process.poll() is not None
        assert time.monotonic() - started < 10
    finally:
        if sandbox.process.poll() is None:
            sandbox.process.kill()
            sandbox.process.wait()


@pytest.mark.parametrize("config", ["resource"], indirect=True)
async def test_hard_killed_parent_leaves_no_listener(
    tmp_path: Path, config: dict[str, Any]
) -> None:
    folder = tmp_path / "artifact"
    generate(
        folder,
        ResourceConfig.model_validate(config),
        Ed25519PrivateKey.generate().public_key(),
        "p1",
    )
    ready = tmp_path / "ready.json"
    script = (
        "import asyncio,json,os,sys\nfrom pathlib import Path\n"
        "from coalitionkit_mint.process import Sandbox\n"
        "async def main():\n"
        " s=Sandbox(Path(sys.argv[1]))\n await s.start()\n"
        " Path(sys.argv[2]).write_text(json.dumps({'pid':os.getpid(),'port':s.port}))\n"
        " await asyncio.sleep(60)\nasyncio.run(main())\n"
    )
    with (tmp_path / "parent.log").open("w") as log:
        parent = subprocess.Popen(
            [sys.executable, "-c", script, str(folder), str(ready)],
            stdout=log,
            stderr=log,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        try:
            for _ in range(400):
                if ready.exists():
                    break
                await asyncio.sleep(0.1)
            assert ready.exists(), (tmp_path / "parent.log").read_text()
            info = json.loads(ready.read_text())
            os.kill(info["pid"], signal.SIGTERM)
            await asyncio.to_thread(parent.wait, 10)
            for _ in range(100):
                try:
                    with socket.create_connection(("127.0.0.1", info["port"]), 0.2):
                        pass
                except OSError:
                    break
                await asyncio.sleep(0.1)
            else:
                pytest.fail("worker survived parent exit")
        finally:
            if parent.poll() is None:
                parent.kill()
                parent.wait(timeout=5)
