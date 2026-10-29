# SPDX-License-Identifier: Apache-2.0
"""Direct dependency and generated media contracts."""

import ast
import sys
import tomllib
import wave
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from .conftest import synthesize


def test_all_direct_imports_declared() -> None:
    package = Path(__file__).resolve().parents[1]
    dependencies = tomllib.loads((package / "pyproject.toml").read_text())["project"][
        "dependencies"
    ]
    distributions = {
        "a2a": "a2a-sdk",
        "PIL": "pillow",
        "google": "protobuf",
        "mcp": "mcp",
        "cryptography": "cryptography",
        "httpx2": "httpx2",
        "pydantic": "pydantic",
        "starlette": "starlette",
        "uvicorn": "uvicorn",
    }
    for path in (package / "src").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
                modules = [node.module.split(".")[0]]
            for module in modules:
                if module in sys.stdlib_module_names or module == "coalitionkit_mint":
                    continue
                distribution = distributions.get(module, module.replace("_", "-"))
                assert any(
                    dep.split("=")[0].split(">")[0].split("[")[0] == distribution
                    for dep in dependencies
                ), (path, module)


@pytest.mark.parametrize("config", ["device"], indirect=True)
def test_device_has_bordered_display(
    config: dict[str, Any],
    media_files: tuple[Path, Path, Path],
) -> None:
    with Image.open(media_files[2]) as image:
        assert image.getpixel((20, 20)) == (0, 0, 0)
        assert image.getpixel((620, 200)) == (0, 0, 0)
        assert image.getpixel((21, 100)) == (0, 0, 0)


def test_voice_is_speech(tmp_path: Path) -> None:
    voice = tmp_path / "speech.wav"
    synthesize(voice, "device")
    with wave.open(str(voice), "rb") as audio:
        assert audio.getnframes() > 16000
        assert audio.getnchannels() == 1 and audio.getsampwidth() == 2
        assert any(audio.readframes(audio.getnframes()))
