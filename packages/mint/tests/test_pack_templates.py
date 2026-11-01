# SPDX-License-Identifier: Apache-2.0
import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import SecretStr

from coalitionkit_contracts import public_key_to_jwk
from coalitionkit_contracts.signing import sign_detached
from coalitionkit_mint.artifact import consent_payload
from coalitionkit_mint.catalog import PackTemplate, TemplateRegistry
from coalitionkit_mint.pipeline import MintFailure, mint
from coalitionkit_models.gateway import FakeModel, ModelGateway, ScriptedResponse
from coalitionkit_models.settings import Settings
from coalitionkit_packs import sign_pack
from coalitionkit_server.app import Server
from coalitionkit_server.settings import Settings as ServerSettings

from .conftest import ScriptedMedia


@pytest.mark.parametrize("config", ["resource"], indirect=True)
@pytest.mark.parametrize("passes", [True, False])
async def test_pack_tests_gate_publication(
    tmp_path: Path, config: dict[str, Any], media_files: tuple[Path, Path, Path], passes: bool
) -> None:
    registry = TemplateRegistry()
    tool = "write" if passes else "list_free_slots"
    registry.register(
        "one",
        {
            "fixture": PackTemplate(
                json.dumps(config), json.dumps({"cases": [{"tool": tool, "arguments_json": "{}"}]})
            )
        },
    )
    with pytest.raises(ValueError, match="not registered"):
        registry.resolve("two", "fixture")
    gateway = ModelGateway(
        Settings(),
        transport=FakeModel(
            [
                ScriptedResponse(
                    '{"records":[{"label":"field_1","value":"42","confidence":0.99}]}'
                ),
                ScriptedResponse('{"cases":[{"tool":"write","arguments_json":"{}"}]}'),
            ]
        ),
    )
    video, voice, _ = media_files
    operation = mint(
        video,
        voice,
        tmp_path / "minted",
        template="fixture",
        coalition_id="one",
        templates=registry,
        owner=Ed25519PrivateKey.generate().public_key(),
        owner_id="owner",
        gateway=gateway,
        media=ScriptedMedia(),
    )
    if not passes:
        with pytest.raises(MintFailure, match="pack steward"):
            await operation
        assert not (tmp_path / "minted" / "agent-card.json").exists()
    else:
        minted = await operation
        try:
            assert minted.coalition_id == "one"
            assert minted.template_name == "fixture"
            assert all(result.passed for result in minted.attacks)
            assert (minted.folder / "agent-card.json").exists()
        finally:
            minted.close()


@pytest.mark.parametrize("config", ["resource"], indirect=True)
async def test_bound_template_enrollment(
    tmp_path: Path, config: dict[str, Any], media_files: tuple[Path, Path, Path]
) -> None:
    folder = tmp_path / "pack"
    shutil.copytree(Path(__file__).parents[2] / "packs/tests/fixtures/pack-gamma", folder)
    (folder / "template.json").write_text(json.dumps(config))
    (folder / "tests.json").write_text('{"cases":[{"tool":"write","arguments_json":"{}"}]}')
    with (folder / "pack.yaml").open("a") as stream:
        stream.write("mint: [{template: template.json, tests: tests.json}]\n")
    author = Ed25519PrivateKey.generate()
    sign_pack(folder, author, "author")
    server = Server(
        ServerSettings(
            packs=[folder],
            pack_trusted_keys={"author": public_key_to_jwk(author.public_key(), "author")},
            store=SecretStr("sqlite:///:memory:"),
            host_key_file=tmp_path / "host.key",
        )
    )
    charter = json.loads(
        (Path(__file__).parents[2] / "server/tests/fixtures/charter.json").read_text()
    )
    charter["pack"] = {"name": "pack-gamma", "version": "1.0.0"}
    charter["roles"] = [{"id": "helper"}]  # a bound charter uses only the pack's roles
    one = server.create(charter)["coalition_id"]
    two = server.create(charter)["coalition_id"]
    templates = server.mint_templates(one)
    with pytest.raises(ValueError, match="not registered"):
        templates.resolve(two, "template.json")
    gateway = ModelGateway(
        Settings(),
        transport=FakeModel(
            [
                ScriptedResponse(
                    '{"records":[{"label":"field_1","value":"42","confidence":0.99}]}'
                ),
                ScriptedResponse('{"cases":[{"tool":"write","arguments_json":"{}"}]}'),
            ]
        ),
    )
    owner = Ed25519PrivateKey.generate()
    video, voice, _ = media_files
    minted = await mint(
        video,
        voice,
        tmp_path / "agent",
        template="template.json",
        coalition_id=one,
        templates=templates,
        owner=owner.public_key(),
        owner_id="owner",
        gateway=gateway,
        media=ScriptedMedia(),
    )
    try:
        with pytest.raises(ValueError, match="another Coalition"):
            server.enroll_minted(two, minted)
        proof = sign_detached(consent_payload(minted.manifest_hash, "approve", {}), owner, "owner")
        minted.approve(proof, owner)
        result = server.enroll_minted(one, minted)
        assert result["coalition_id"] == one
        assert minted.sandbox.url in server.hosts[one].cards
        assert minted.sandbox.url not in server.hosts[two].cards
    finally:
        minted.close()
        server.close()
