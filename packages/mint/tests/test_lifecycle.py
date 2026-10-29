# SPDX-License-Identifier: Apache-2.0
"""Owner discovery, catalog contracts and failure recovery."""

import json
import re
from pathlib import Path
from typing import Any, cast

import httpx2
import pytest
from a2a.types import AgentCard
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from google.protobuf.json_format import ParseDict

from coalitionkit_contracts.signing import sign_detached
from coalitionkit_edges.a2a.identity import CardRegistry
from coalitionkit_mint import acceptance, pipeline
from coalitionkit_mint.artifact import connect, consent_payload, digest, generate
from coalitionkit_mint.process import Sandbox
from coalitionkit_mint.prove import AttackResult
from coalitionkit_mint.publish import Minted, publish
from coalitionkit_mint.schema import ResourceConfig
from coalitionkit_models.gateway import FakeModel, ModelGateway
from coalitionkit_models.settings import Settings

from .conftest import ScriptedMedia


@pytest.fixture
def pending(tmp_path: Path, config: dict[str, Any]) -> tuple[Minted, Ed25519PrivateKey]:
    owner = Ed25519PrivateKey.generate()
    folder = tmp_path / "artifact"
    model = ResourceConfig.model_validate(config)
    manifest = generate(folder, model, owner.public_key(), "p1")
    sandbox = Sandbox(folder)
    sandbox.url = "http://127.0.0.1:12345/mcp"
    publish(folder, sandbox, model)
    return Minted(folder, sandbox, manifest, [AttackResult("bounds", True)], 1, 0, 0), owner


@pytest.mark.parametrize("config", ["resource"], indirect=True)
async def test_card_owner_and_pending_gate(pending: tuple[Minted, Ed25519PrivateKey]) -> None:
    minted, owner = pending
    try:
        await minted.sandbox.start()
        async with httpx2.AsyncClient(trust_env=False) as http:
            card = await http.get(
                minted.sandbox.url.replace("/mcp", "/.well-known/agent-card.json")
            )
            params = card.json()["capabilities"]["extensions"][0]["params"]
            assert params["state"] == "pending" and params["keys"] == []
            for method in (
                "initialize",
                "server/discover",
                "tools/list",
                "resources/list",
                "prompts/list",
                "ping",
                "future/method",
            ):
                response = await http.post(
                    minted.sandbox.url,
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": method,
                        "params": {},
                    },
                    headers={
                        "accept": "application/json, text/event-stream",
                        "mcp-protocol-version": "2026-07-28",
                    },
                )
                assert response.status_code == 403
                assert response.json()["error"] == "owner approval required"
        proof = sign_detached(consent_payload(minted.manifest_hash, "approve", {}), owner, "owner")
        with pytest.raises(ValueError, match="signer"):
            minted.approve(proof, Ed25519PrivateKey.generate())
        minted.approve(proof, owner)
        data = json.loads((minted.folder / "agent-card.json").read_text())
        params = data["capabilities"]["extensions"][0]["params"]
        assert params["approval_proof_hash"] == digest(proof)
        assert params["keys"][0]["x"] == params["owner"]["x"]
        CardRegistry("mint").admit(minted.sandbox.url, ParseDict(data, AgentCard()))
    finally:
        minted.close()


@pytest.mark.parametrize("config", ["resource"], indirect=True)
def test_catalog_contract(pending: tuple[Minted, Ed25519PrivateKey]) -> None:
    minted, _ = pending
    try:
        catalog_path = Path(__file__).resolve().parents[3] / "spec/catalog/coalitionkit-v0_9.json"
        catalog = json.loads(catalog_path.read_text())["components"]
        data = minted.catalog_data()
        tests = data["AttackTests"]["tests"]
        doc = catalog["AttackTests"]["props"]["tests"]["doc"]
        kinds = re.search(r"kind: ([a-z|]+)", doc)
        assert kinds
        for item in tests:
            assert set(item) == {"name", "kind", "state", "log"}
            assert item["kind"] in kinds.group(1).split("|")
            assert item["state"] in catalog["AttackTests"]["states"]
        stages = data["MintPipeline"]["stages"]
        doc = catalog["MintPipeline"]["props"]["stages"]["doc"]
        names = re.search(r"name: ([a-z|]+)", doc)
        assert names
        assert [item["name"] for item in stages] == names.group(1).split("|")
        assert all(set(item) == {"name", "state", "took", "detail", "artifacts"} for item in stages)
    finally:
        minted.close()


@pytest.mark.parametrize("config", ["resource"], indirect=True)
async def test_remint_failure_keeps_approved(
    pending: tuple[Minted, Ed25519PrivateKey],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    minted, owner = pending
    proof = sign_detached(consent_payload(minted.manifest_hash, "approve", {}), owner, "owner")
    minted.approve(proof, owner)

    async def fail(*args: Any, **kwargs: Any) -> Minted:
        raise pipeline.MintFailure("design failed")

    monkeypatch.setattr(pipeline, "mint", fail)
    try:
        with pytest.raises(pipeline.MintFailure, match="design failed"):
            await pipeline.remint(
                minted,
                tmp_path / "video",
                tmp_path / "voice",
                tmp_path / "new",
                template="resource",
                owner=owner.public_key(),
                owner_id="p1",
                gateway=ModelGateway(Settings(), transport=FakeModel([])),
                media=ScriptedMedia(),
            )
        with connect(minted.folder) as db:
            assert db.execute("SELECT state, proof FROM lifecycle").fetchone() == (
                "approved",
                proof,
            )
    finally:
        minted.close()


@pytest.mark.parametrize("failure", ["start", "close"])
async def test_acceptance_continues_and_uses_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    calls: list[str] = []

    class FailedClose:
        def scorecard(self) -> dict[str, Any]:
            return {"passed": True}

        def close(self) -> None:
            raise OSError("shutdown failed")

    async def fail(*args: Any, **kwargs: Any) -> Minted:
        calls.append(kwargs["template"])
        assert args[3] == tmp_path / "output" / ("scorecard-" + kwargs["template"] + ".json")
        if failure == "start":
            raise OSError("output unavailable")
        return cast("Minted", FailedClose())

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("COALITIONKIT_META_API_KEY", "test-placeholder")
    monkeypatch.setenv("COALITIONKIT_LIVE", "1")
    monkeypatch.setattr(acceptance, "run_one", fail)
    monkeypatch.setattr(
        "sys.argv",
        [
            "mint",
            "--resource-video",
            "r.mp4",
            "--resource-voice",
            "r.wav",
            "--device-video",
            "d.mp4",
            "--device-voice",
            "d.wav",
            "--output",
            str(tmp_path / "output"),
        ],
    )
    with pytest.raises(SystemExit) as exc:
        await acceptance.main()
    assert exc.value.code == 1 and calls == ["resource", "device"]


@pytest.mark.parametrize("config", ["resource"], indirect=True)
def test_publish_stage_waits_for_approval(pending: tuple[Minted, Ed25519PrivateKey]) -> None:
    minted, owner = pending
    try:
        stage = minted.catalog_data()["MintPipeline"]["stages"][-1]
        assert stage["state"] == "pending" and stage["took"] is None
        proof = sign_detached(consent_payload(minted.manifest_hash, "approve", {}), owner, "owner")
        minted.approve(proof, owner)
        stage = minted.catalog_data()["MintPipeline"]["stages"][-1]
        assert stage["state"] == "done" and stage["took"] > 0
    finally:
        minted.close()
