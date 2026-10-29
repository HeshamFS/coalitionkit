# SPDX-License-Identifier: Apache-2.0
"""Acceptance 6 against the real Meta models; no saved inputs or credentials."""

import json
import os
from pathlib import Path
from typing import Any, Literal, cast

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coalitionkit_contracts.signing import sign_detached
from coalitionkit_mint.acceptance import run_one
from coalitionkit_mint.artifact import consent_payload
from coalitionkit_mint.prove import rejected
from coalitionkit_mint.reader import append_frame
from coalitionkit_models.gateway import ModelGateway
from coalitionkit_models.media import MediaClient
from coalitionkit_models.meter import CostMeter
from coalitionkit_models.prices import load_price_table
from coalitionkit_models.settings import load_settings

from .conftest import synthesize


@pytest.mark.live
@pytest.mark.parametrize("config", ["resource", "device"], indirect=True)
async def test_live_mint(
    tmp_path: Path, config: dict[str, Any], media_files: tuple[Path, Path, Path]
) -> None:
    if not os.environ.get("COALITIONKIT_META_API_KEY"):
        pytest.skip("no key")
    if os.environ.get("COALITIONKIT_LIVE") != "1":
        pytest.skip("COALITIONKIT_LIVE is not 1")
    video, voice, frame = media_files
    synthesize(voice, config["template"])
    settings = load_settings()
    meter = CostMeter(load_price_table())
    gateway = ModelGateway(settings, meter=meter)
    media = MediaClient(settings, meter=meter)
    owner = Ed25519PrivateKey.generate()
    try:
        result = await run_one(
            video,
            voice,
            tmp_path / "live",
            tmp_path / "scorecard-live.json",
            template=cast("Literal['resource', 'device']", config["template"]),
            gateway=gateway,
            media=media,
            owner=owner,
        )
        try:
            print(json.dumps(result.scorecard()))
            assert result.scorecard()["passed"]
            tool = "status" if config["template"] == "device" else "list_free_slots"
            async with result.sandbox.client() as client:
                assert await rejected(client, tool, {})
            result.approve(
                sign_detached(consent_payload(result.manifest_hash, "approve", {}), owner, "owner")
            )
            if config["template"] == "device":
                assert await append_frame(result.folder, frame, media, gateway) > 0
            async with result.sandbox.client() as client:
                assert not (await client.call_tool(tool, {})).is_error
        finally:
            result.close()
    finally:
        await gateway.aclose()
        await media.aclose()
