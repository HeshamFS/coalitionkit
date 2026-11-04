# SPDX-License-Identifier: Apache-2.0
"""`coalitionkit up` finds its files in a checkout and in a wheel, and says why it cannot start."""

import os
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from coalitionkit_cli import up
from coalitionkit_cli.main import main
from coalitionkit_contracts.resources import checkout_root, spec_path


def _web(tmp_path: Path, *, built: bool, modules: bool = True) -> Path:
    web = tmp_path / "web"
    (web / "src").mkdir(parents=True)
    (web / "src" / "main.tsx").write_text("source")
    os.utime(web / "src" / "main.tsx", (100, 100))
    if modules:
        (web / "node_modules").mkdir()
    if built:
        (web / "dist").mkdir()
        (web / "dist" / "index.html").write_text("room")
    return web


def test_this_test_run_is_a_checkout_and_reads_its_own_spec() -> None:
    root = checkout_root()
    assert root is not None
    assert spec_path("schemas") == root / "spec" / "schemas"
    assert spec_path("schemas").is_dir()


def test_a_built_checkout_serves_its_build_without_npm(tmp_path: Path) -> None:
    web = _web(tmp_path, built=True)
    with patch("shutil.which", side_effect=AssertionError("npm not needed")):
        assert up.checkout_web(web) == web / "dist"


def test_an_unbuilt_checkout_builds_once(tmp_path: Path) -> None:
    web = _web(tmp_path, built=False, modules=False)
    with (
        patch("shutil.which", return_value="npm"),
        patch("subprocess.run") as run,
    ):
        assert up.checkout_web(web) == web / "dist"
    assert [call.args[0][1] for call in run.call_args_list] == ["ci", "run"]
    assert all(call.kwargs["cwd"] == web for call in run.call_args_list)


def test_an_unbuilt_checkout_without_npm_says_what_to_install(tmp_path: Path) -> None:
    web = _web(tmp_path, built=False)
    with (
        patch("shutil.which", return_value=None),
        pytest.raises(FileNotFoundError, match="Install Node 22"),
    ):
        up.checkout_web(web)


def test_source_newer_than_the_build_rebuilds_or_warns(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    web = _web(tmp_path, built=True)
    os.utime(web / "dist" / "index.html", (50, 50))
    with (
        patch("shutil.which", return_value="npm"),
        patch("subprocess.run") as run,
    ):
        up.checkout_web(web)
    assert [call.args[0][1] for call in run.call_args_list] == ["run"]
    with patch("shutil.which", return_value=None):
        assert up.checkout_web(web) == web / "dist"
    assert "older than its source" in capsys.readouterr().out


def test_a_failed_build_names_the_command(tmp_path: Path) -> None:
    web = _web(tmp_path, built=False)
    failure = subprocess.CalledProcessError(3, "npm")
    with (
        patch("shutil.which", return_value="npm"),
        patch("subprocess.run", side_effect=failure),
        pytest.raises(OSError, match=r"`npm run build` failed.*exit 3"),
    ):
        up.checkout_web(web)


def test_an_install_without_room_files_says_how_to_recover(tmp_path: Path) -> None:
    with (
        patch.object(up, "checkout_root", return_value=None),
        patch.object(up, "resource_path", return_value=tmp_path),
        pytest.raises(FileNotFoundError, match="--no-web"),
    ):
        up.web_dist()


def test_up_leads_with_the_sentence_and_makes_no_demo(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("COALITIONKIT_META_API_KEY", raising=False)
    room = tmp_path / "room"
    room.mkdir()
    (room / "index.html").write_text("room")
    with (
        patch.object(up, "web_dist", return_value=room),
        patch("uvicorn.Server.serve", new=AsyncMock()),
    ):
        assert main(["up", "--data-dir", str(tmp_path / "data")]) == 0
    printed = capsys.readouterr().out
    assert "say what needs doing in one sentence" in printed
    assert "built-in rules" in printed
    assert "Viewer token" not in printed
    assert "#start=" not in printed
    assert not (tmp_path / "data" / "demo-coalition").exists()


def test_up_prints_the_real_reason(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    reason = "the web room is not built and npm was not found."
    with patch.object(up, "web_dist", side_effect=FileNotFoundError(reason)):
        assert main(["up", "--data-dir", str(tmp_path / "data")]) == 2
    assert capsys.readouterr().err == f"Could not start: {reason}\n"
