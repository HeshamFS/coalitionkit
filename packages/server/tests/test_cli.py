# SPDX-License-Identifier: Apache-2.0
"""The installed command starts a real process and serves health and admin calls."""

import json
import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

import httpx


def test_installed_cli_serves_and_administers(tmp_path: Path) -> None:
    executable = shutil.which("coalitionkit-server")
    assert executable is not None
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = int(sock.getsockname()[1])
    base = f"http://127.0.0.1:{port}"
    environment = {
        **os.environ,
        "COALITIONKIT_STORE": f"sqlite:///{tmp_path / 'store.db'}",
        "COALITIONKIT_HOST_KEY_FILE": str(tmp_path / "key"),
        "COALITIONKIT_PUBLIC_BASE_URL": base,
        "COALITIONKIT_BIND_PORT": str(port),
        "COALITIONKIT_ADMIN_TOKEN": "cli-test-secret",
    }
    process = subprocess.Popen(
        [executable, "serve"],
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    try:
        deadline = time.monotonic() + 60  # a cold start imports every package
        with httpx.Client(base_url=base, timeout=1) as client:
            while True:
                assert process.poll() is None, process.communicate()[1]
                try:
                    response = client.get("/healthz")
                    break
                except httpx.TransportError:
                    assert time.monotonic() < deadline
                    time.sleep(0.05)
            assert response.status_code == 200
            assert response.json()["store"] == "ok"
            assert "cli-test-secret" not in response.text
            assert client.get("/admin/status").status_code == 401
        created = subprocess.run(
            [
                executable,
                "init-coalition",
                "--charter",
                str(Path(__file__).parent / "fixtures" / "charter.json"),
            ],
            env=environment,
            capture_output=True,
            text=True,
            check=True,
        )
        coalition = json.loads(created.stdout)["coalition_id"]
        status = subprocess.run(
            [executable, "status"], env=environment, capture_output=True, text=True, check=True
        )
        assert json.loads(status.stdout)["coalitions"][0]["coalition_id"] == coalition
        invitation = subprocess.run(
            [executable, "invite", coalition, "p2"],
            env=environment,
            capture_output=True,
            text=True,
            check=True,
        )
        assert json.loads(invitation.stdout)["invitation"]
    finally:
        process.terminate()
        process.communicate(timeout=10)
