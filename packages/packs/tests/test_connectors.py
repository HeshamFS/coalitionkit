# SPDX-License-Identifier: Apache-2.0
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from coalitionkit_packs.cli import connector_command, connector_environment, main

FIXTURE = Path(__file__).parent / "fixtures" / "pack-gamma"


def test_connector_preview_and_environment(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("COALITIONKIT_STORE", "secret-store")
    monkeypatch.setenv("OPENAI_API_KEY", "secret-key")
    monkeypatch.setenv("HOST_DATA_DIR", "secret-dir")
    env = connector_environment()
    assert not {"COALITIONKIT_STORE", "OPENAI_API_KEY", "HOST_DATA_DIR"} & env.keys()
    assert (
        main(["connectors", str(FIXTURE), "--host", "http://localhost:8000", "--coalition", "one"])
        == 0
    )
    preview = json.loads(capsys.readouterr().out)
    assert preview["command"] == ["python", "probe.py"]
    assert preview["cwd"] == "connectors/probe"


def test_connector_filesystem_boundary(tmp_path: Path) -> None:
    docker = shutil.which("docker")
    if not docker or subprocess.run([docker, "info"], capture_output=True).returncode:
        pytest.skip("Docker isolation engine unavailable")
    folder = tmp_path / "pack"
    shutil.copytree(FIXTURE, folder)
    secret_paths: list[str] = []
    for name in ["store.sqlite", "host.key", "admin.token", "member.credentials"]:
        secret = tmp_path / name
        secret.write_text("PRIVATE_CANARY_" + name)
        secret_paths.append(str(secret))
    probe = folder / "connectors/probe/probe.py"
    text = probe.read_text()
    start, end = text.index("paths = "), text.index("\nresults =")
    probe.write_text(text[:start] + "paths = " + repr(secret_paths) + text[end:])
    command = connector_command(
        "python:3.15-slim", folder, "probe", ["python", "probe.py"], "http://host/join#one-use"
    )
    result = subprocess.run(
        command, env=connector_environment(), capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert set(report["reads"].values()) == {"denied"}
    assert report["cwd"] == "/pack/connectors/probe"
    assert report["env"]["HOME"] == "/tmp"
    assert not any(key.startswith("COALITIONKIT_") for key in report["env"])
    assert "PRIVATE_CANARY" not in result.stdout + result.stderr
