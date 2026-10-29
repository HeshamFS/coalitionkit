# SPDX-License-Identifier: Apache-2.0
"""Policy invariants independent of model replies and MCP argument coercion."""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coalitionkit_contracts import SignatureError
from coalitionkit_contracts.signing import sign_detached
from coalitionkit_mint.artifact import consent_payload, generate, load
from coalitionkit_mint.perceive import extract
from coalitionkit_mint.schema import ResourceConfig
from coalitionkit_mint.worker import Operations


@pytest.mark.parametrize("config", ["resource"], indirect=True)
def test_bounds_and_prerequisites(tmp_path: Path, config: dict[str, Any]) -> None:
    config["prerequisites"] = ["ready"]
    config["limit"] = 1
    owner = Ed25519PrivateKey.generate()
    folder = tmp_path / "artifact"
    manifest_hash = generate(
        folder, ResourceConfig.model_validate(config), owner.public_key(), "p1"
    )
    ops = Operations(folder)
    args: dict[str, Any] = {"start": 540, "end": 570, "prerequisites": ["ready"]}
    with pytest.raises(SignatureError):
        ops.invoke("hold_slot", args)

    def signed(arguments: dict[str, Any]) -> str:
        return sign_detached(consent_payload(manifest_hash, "hold_slot", arguments), owner, "owner")

    invalid: list[dict[str, Any]] = [
        {**args, "prerequisites": []},
        {**args, "start": 0, "end": 30},
        {**args, "end": 560},
        {**args, "start": True},
    ]
    for bad in invalid:
        with pytest.raises(ValueError):
            ops.invoke("hold_slot", bad, signed(bad))
    assert ops.invoke("hold_slot", args, signed(args))["state"] == "held"
    next_args = {**args, "start": 570, "end": 600}
    with pytest.raises(ValueError, match="limit"):
        ops.invoke("hold_slot", next_args, signed(next_args))
    altered = {**config, "limit": 2}
    (folder / "config.json").write_text(json.dumps(altered))
    with pytest.raises(ValueError, match="integrity"):
        load(folder)


@pytest.mark.parametrize("config", ["resource"], indirect=True)
def test_atomic_holds_and_distinct_manifests(tmp_path: Path, config: dict[str, Any]) -> None:
    owner = Ed25519PrivateKey.generate()
    model = ResourceConfig.model_validate(config)
    first = generate(tmp_path / "first", model, owner.public_key(), "p1")
    second = generate(tmp_path / "second", model, owner.public_key(), "p1")
    assert first != second
    ops = Operations(tmp_path / "first")

    def hold(index: int) -> bool:
        try:
            ops.invoke("hold_slot", {"start": 540, "end": 570, "prerequisites": []})
            return True
        except ValueError:
            return False

    with ThreadPoolExecutor(max_workers=4) as pool:
        assert sum(pool.map(hold, range(4))) == 1


def test_capture_refuses_nonvideo(tmp_path: Path) -> None:
    source = tmp_path / "input.txt"
    source.write_text("not a video")
    with pytest.raises(ValueError, match="recorded video"):
        extract(source, tmp_path / "frames")
