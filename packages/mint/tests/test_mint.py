# SPDX-License-Identifier: Apache-2.0
"""Real subprocess MCP tests with scripted model and media replies."""

import json
import socket
from pathlib import Path
from typing import Any, Literal, cast

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from mcp.shared.exceptions import MCPError

from coalitionkit_contracts import SignatureError
from coalitionkit_contracts.signing import sign_detached
from coalitionkit_mint.acceptance import run_one
from coalitionkit_mint.artifact import consent_payload
from coalitionkit_mint.pipeline import MintFailure, mint, model_config
from coalitionkit_mint.process import scrub_environment
from coalitionkit_mint.prove import rejected
from coalitionkit_mint.reader import append_frame
from coalitionkit_mint.scan import scan_templates
from coalitionkit_models.gateway import FakeModel, ModelGateway, ScriptedResponse

from .conftest import ScriptedMedia


@pytest.mark.parametrize("config", ["resource", "device"], indirect=True)
async def test_end_to_end(
    tmp_path: Path,
    config: dict[str, Any],
    media_files: tuple[Path, Path, Path],
    scripted: tuple[ModelGateway, ScriptedMedia, FakeModel],
) -> None:
    gateway, media, fake = scripted
    video, voice, frame = media_files
    owner = Ed25519PrivateKey.generate()
    result = await run_one(
        video,
        voice,
        tmp_path / "minted",
        tmp_path / "scorecard.json",
        template=cast("Literal['resource', 'device']", config["template"]),
        gateway=gateway,
        media=media,
        owner=owner,
    )
    try:
        assert result.elapsed_seconds < 90
        assert result.cost_micro_usd > 0
        assert result.tokens > 0
        assert all(attack.passed for attack in result.attacks)
        assert json.loads((tmp_path / "scorecard.json").read_text())["passed"]
        assert (result.folder / "agent-card.json").exists()
        assert (result.folder / "SKILL.md").exists()
        assert result.catalog_data()["MintedAgentCard"]["health"] == "pending"
        tool = "status" if config["template"] == "device" else "list_free_slots"
        with pytest.RaisesGroup(
            pytest.RaisesExc(MCPError, match="Server returned an error response"),
            flatten_subgroups=True,
        ):
            async with result.sandbox.client():
                pytest.fail("pending connection accepted")
        stages = result.catalog_data()["MintPipeline"]["stages"]
        assert all(s["state"] == "done" and s["took"] >= 0 for s in stages[:-1])
        assert stages[-1]["state"] == "pending" and stages[-1]["took"] is None
        payload = consent_payload(result.manifest_hash, "approve", {})
        with pytest.raises(SignatureError):
            result.approve(sign_detached(payload, Ed25519PrivateKey.generate(), "owner"), owner)
        stale = consent_payload("0" * 64, "approve", {})
        with pytest.raises(SignatureError):
            result.approve(sign_detached(stale, owner, "owner"), owner)
        result.approve(sign_detached(payload, owner, "owner"), owner)
        assert result.catalog_data()["MintPipeline"]["stages"][-1]["state"] == "done"
        assert result.catalog_data()["MintPipeline"]["stages"][-1]["took"] >= 0
        async with result.sandbox.client() as client:
            assert not (await client.call_tool(tool, {})).is_error
            if config["template"] == "resource":
                args: dict[str, Any] = {
                    "start": 540,
                    "end": 570,
                    "prerequisites": [],
                }
                held = await client.call_tool("hold_slot", args)
                assert not held.is_error
                assert await rejected(client, "hold_slot", args, "occupied")
                operation_args = dict(held.structured_content or {})
                operation_args.pop("state")
                for operation in ("confirm", "cancel"):
                    proof = sign_detached(
                        consent_payload(result.manifest_hash, operation, operation_args),
                        owner,
                        "owner",
                    )
                    updated = await client.call_tool(
                        operation, {**operation_args, "signature": proof}
                    )
                    assert not updated.is_error
                    operation_args = dict(updated.structured_content or {})
                    operation_args.pop("state")
            else:
                fake.script.append(
                    ScriptedResponse(
                        '{"records":[{"label":"Field 1","value":"42","confidence":0.99}]}'
                    )
                )
                assert await append_frame(result.folder, frame, media, gateway) == 1
                reading = await client.call_tool("read_field_1", {})
                assert reading.structured_content == {
                    "value": 42.0,
                    "observed": reading.structured_content["observed"],
                }
                assert not (await client.call_tool("alarm", {})).is_error
                assert await rejected(client, "write", {}, "Unknown tool")
        result.pause()
        with pytest.RaisesGroup(
            pytest.RaisesExc(MCPError, match="Server returned an error response"),
            flatten_subgroups=True,
        ):
            async with result.sandbox.client():
                pytest.fail("pending connection accepted")
        result.delete()
        assert result.sandbox.process is not None and result.sandbox.process.poll() is not None
        assert not result.folder.exists()
        with (
            pytest.raises(OSError),
            socket.create_connection(("127.0.0.1", result.sandbox.port), 1),
        ):
            pytest.fail("worker still listening after delete")
    finally:
        result.close()


@pytest.mark.parametrize("config", ["resource"], indirect=True)
async def test_failed_attack_blocks_publish(
    tmp_path: Path,
    config: dict[str, Any],
    media_files: tuple[Path, Path, Path],
    scripted: tuple[ModelGateway, ScriptedMedia, FakeModel],
) -> None:
    gateway, media, fake = scripted
    fake.script[-1] = ScriptedResponse(
        '{"cases":[{"tool":"list_free_slots","arguments_json":"{}"}]}'
    )
    with pytest.raises(MintFailure, match="publication blocked"):
        await mint(
            media_files[0],
            media_files[1],
            tmp_path / "failed",
            template="resource",
            owner=Ed25519PrivateKey.generate().public_key(),
            owner_id="p1",
            gateway=gateway,
            media=media,
        )
    assert not (tmp_path / "failed" / "agent-card.json").exists()


@pytest.mark.parametrize("config", ["resource"], indirect=True)
async def test_one_repair(
    config: dict[str, Any], scripted: tuple[ModelGateway, ScriptedMedia, FakeModel]
) -> None:
    gateway, _, fake = scripted
    fake.script[:] = [ScriptedResponse("{}"), ScriptedResponse(json.dumps(config))]
    assert (await model_config(gateway, "resource", "rules", "mint-test")).template == "resource"
    assert len(fake.calls) == 2
    assert fake.calls[0][2]["response_format"]["json_schema"]["strict"]
    fake.script[:] = [ScriptedResponse("{}"), ScriptedResponse("{}")]
    with pytest.raises(MintFailure, match="one repair"):
        await model_config(gateway, "resource", "rules", "mint-test")


def test_template_scan(tmp_path: Path) -> None:
    import coalitionkit_mint

    scan_templates(Path(coalitionkit_mint.__file__).parent / "templates")
    for source in (
        "import socket",
        "from urllib.request import urlopen",
        "import importlib",
        "__import__('socket')",
        "exec('pass')",
    ):
        (tmp_path / "bad.py").write_text(source)
        with pytest.raises(ValueError):
            scan_templates(tmp_path)


def test_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COALITIONKIT_META_API_KEY", "never-in-worker")
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.invalid")
    monkeypatch.setenv("PYTHONPATH", "untrusted")
    assert (
        not {"COALITIONKIT_META_API_KEY", "HTTPS_PROXY", "PYTHONPATH"} & scrub_environment().keys()
    )
