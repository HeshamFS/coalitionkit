# SPDX-License-Identifier: Apache-2.0
"""Exercise the console process, persistent host and same-origin room."""

import asyncio
import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from test_server import Running

from coalitionkit_cli.demo import demo_start
from coalitionkit_cli.main import main
from coalitionkit_cli.storage import admin_token, prepare
from coalitionkit_cli.web import Room
from coalitionkit_mcp.gateway import build_envelope
from coalitionkit_server import Settings, create_server


def test_conform_missing(capsys: pytest.CaptureFixture[str]) -> None:
    missing = ModuleNotFoundError(name="coalitionkit_conformance")
    with patch("coalitionkit_cli.main.importlib.import_module", side_effect=missing):
        assert main(["conform"]) == 2
    assert capsys.readouterr().out == "The conformance package is not installed.\n"


def test_reset_is_bounded(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        prepare(tmp_path, True)
    data = prepare(tmp_path / "owned", False)
    (data / "old").write_text("old")
    assert prepare(data, True) == data
    assert not (data / "old").exists()
    token = admin_token(data)
    assert token == admin_token(data)
    if os.name != "nt":
        assert (data / "admin.token").stat().st_mode & 0o077 == 0


def test_static_and_redeem(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<h1>Room</h1>")
    app = create_server(
        Settings(
            store=SecretStr(f"sqlite:///{tmp_path / 'host.db'}"),
            host_key_file=tmp_path / "host.key",
            admin_token=SecretStr("test-admin"),
        )
    )
    with TestClient(Room(app, dist)) as client:
        assert client.get("/").text == "<h1>Room</h1>"
        assert client.get("/confirm/code").text == "<h1>Room</h1>"
        assert client.get("/healthz").status_code == 200
        assert client.get("/v1/feed").status_code == 401
        assert client.get("/mcp").status_code != 404
        charter = {
            "goal": "Agree on tasks",
            "roles": [{"id": "member"}],
            "rules": [],
            "deadline": "2099-12-31T00:00:00Z",
            "deciders": ["p1"],
        }
        response = client.post(
            "/admin/coalitions", json=charter, headers={"Authorization": "Bearer test-admin"}
        )
        assert response.status_code == 200
        invite = response.json()["invitations"][0]["invitation"]
        response = client.post("/invitations/redeem", json={"invitation": invite})
        assert response.status_code == 200
        assert response.json()["participant"] == "p1"
        assert response.json()["token"]


def read_snapshot(base: str, token: str, member: str, path: str = "/v1/feed") -> dict[str, Any]:
    with httpx.stream("GET", base + path, headers={"Authorization": f"Bearer {token}"}) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        for line in response.iter_lines():
            if not line.startswith("data:"):
                continue
            event = json.loads(line.removeprefix("data:"))
            if event["type"] == "RUN_STARTED":
                assert f":{member}:" in event["threadId"]
                if path == "/v1/agent":
                    return event
            if event["type"] == "STATE_SNAPSHOT":
                return event["snapshot"]
    raise AssertionError("stream ended without a snapshot")


def test_up_process(tmp_path: Path) -> None:
    data = tmp_path / "data"
    output = tmp_path / "output.txt"
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    env = {key: value for key, value in os.environ.items() if not key.startswith("COALITIONKIT_")}
    start = time.monotonic()
    with output.open("w", encoding="utf-8") as stream:
        process = subprocess.Popen(
            [
                str(
                    Path(sys.executable).with_name(
                        "coalitionkit.exe" if os.name == "nt" else "coalitionkit"
                    )
                ),
                "up",
                "--no-web",
                "--demo",
                "--data-dir",
                str(data),
            ],
            stdout=stream,
            stderr=stream,
            env=env,
            creationflags=flags,
        )
        try:
            base = ""
            while time.monotonic() - start < 15:
                text = output.read_text(encoding="utf-8")
                match = re.search(r"Host: (http://127.0.0.1:\d+)", text)
                if match:
                    base = match[1]
                    try:
                        if httpx.get(base + "/healthz", timeout=0.3).status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                assert process.poll() is None, text
                time.sleep(0.05)
            else:
                pytest.fail(output.read_text(encoding="utf-8"))
            print(f"Startup to healthy: {time.monotonic() - start:.2f}s")
            assert time.monotonic() - start < 15
            text = output.read_text(encoding="utf-8")
            credentials = re.findall(r"Sign in: (p\d+) \S+ Viewer token: (\S+)", text)
            assert len(credentials) == 3
            token = (data / "admin.token").read_text()
            assert token not in text
            status = httpx.get(base + "/admin/status", headers={"Authorization": f"Bearer {token}"})
            assert len(status.json()["coalitions"]) == 1
            assert status.json()["coalitions"][0]["members"] == 3
            for member, credential in credentials:
                snapshot = read_snapshot(base, credential, member)
                assert snapshot["coalition_id"] == status.json()["coalitions"][0]["coalition_id"]
                read_snapshot(base, credential, member, "/v1/agent")
            event_count = status.json()["coalitions"][0]["events"]
            process.send_signal(signal.CTRL_BREAK_EVENT if os.name == "nt" else signal.SIGINT)
            assert process.wait(timeout=15) == 0
            with socket.socket() as probe:
                assert probe.connect_ex(("127.0.0.1", int(base.rsplit(":", 1)[1]))) != 0
            # Restart must reuse the host identity rather than choose a different free port.
            saved = int((data / "port").read_text())
            assert saved == int(base.rsplit(":", 1)[1])
            # A second run on the same data keeps its one demo Coalition.
            again = tmp_path / "again.txt"
            with again.open("w", encoding="utf-8") as second:
                process = subprocess.Popen(
                    process.args, stdout=second, stderr=second, env=env, creationflags=flags
                )
            until = time.monotonic() + 15
            while "created earlier" not in again.read_text(encoding="utf-8"):
                assert process.poll() is None and time.monotonic() < until, again.read_text()
                time.sleep(0.05)
            while True:
                try:
                    if httpx.get(base + "/healthz", timeout=0.3).status_code == 200:
                        break
                except httpx.TransportError:
                    assert time.monotonic() < until
                    time.sleep(0.05)
            status = httpx.get(base + "/admin/status", headers={"Authorization": f"Bearer {token}"})
            assert len(status.json()["coalitions"]) == 1
            assert "Viewer token:" not in again.read_text(encoding="utf-8")
            assert status.json()["coalitions"][0]["events"] == event_count
            read_snapshot(base, credentials[0][1], credentials[0][0])
            process.send_signal(signal.CTRL_BREAK_EVENT if os.name == "nt" else signal.SIGINT)
            assert process.wait(timeout=15) == 0
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)


def test_room_printed_tokens_are_scoped(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    settings = Settings(
        store=SecretStr(f"sqlite:///{tmp_path / 'host.db'}"),
        host_key_file=tmp_path / "host.key",
        bind_port=port,
        public_base_url=f"http://127.0.0.1:{port}",
    )
    running = Running(settings)
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<h1>Room</h1>")
    running.worker.config.app = Room(running.app, dist)
    with running:
        demo_start(running.state, tmp_path, 2, running.base)
        printed = capsys.readouterr().out
        credentials = re.findall(r"Sign in: (p\d+) \S+ Viewer token: (\S+)", printed)
        assert len(credentials) == 2
        coalition = (tmp_path / "demo-coalition").read_text()
        person = running.state.registry.hosted_for(coalition, "p1")
        observation = build_envelope(
            person,
            coalition,
            "coalition.observe",
            {"source": "chat", "content": "private-observation-p1"},
            scope={"audience": "self"},
        )
        reply = asyncio.run(running.state.accept(observation, person.card_url))
        assert "error" not in reply, reply
        assert httpx.get(running.base + "/").text == "<h1>Room</h1>"
        for member, token in credentials:
            snapshot = read_snapshot(running.base, token, member)
            assert snapshot["coalition_id"] == coalition
            assert ("private-observation-p1" in json.dumps(snapshot)) == (member == "p1")
            read_snapshot(running.base, token, member, "/v1/agent")
