# SPDX-License-Identifier: Apache-2.0
"""Regression coverage for consent, input decoding and model evidence."""

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from PIL import Image

from coalitionkit_contracts import SignatureError
from coalitionkit_contracts.signing import sign_detached
from coalitionkit_mint.artifact import connect, consent_payload, generate
from coalitionkit_mint.perceive import extract, read_frame
from coalitionkit_mint.pipeline import model_config
from coalitionkit_mint.reader import append_frame
from coalitionkit_mint.schema import DeviceConfig, ResourceConfig
from coalitionkit_mint.worker import Operations
from coalitionkit_models.gateway import FakeModel, ModelGateway, ScriptedResponse
from coalitionkit_models.sam import Box, Segment
from coalitionkit_models.settings import Settings

from .conftest import ScriptedMedia


@pytest.mark.parametrize("config", ["resource"], indirect=True)
def test_consent_binds_hold_and_revision(tmp_path: Path, config: dict[str, Any]) -> None:
    owner = Ed25519PrivateKey.generate()
    folder = tmp_path / "artifact"
    manifest = generate(folder, ResourceConfig.model_validate(config), owner.public_key(), "p1")
    ops = Operations(folder)
    base: dict[str, Any] = {"start": 540, "end": 570, "prerequisites": []}
    with pytest.raises(ValueError, match="invalid fields"):
        ops.invoke("hold_slot", {**base, "id": "squatted"})
    held = ops.invoke("hold_slot", base, "unverified")
    held.pop("state")
    with connect(folder) as db:
        assert db.execute("SELECT count(*) FROM consumed_proofs").fetchone()[0] == 0
    cancel = sign_detached(consent_payload(manifest, "cancel", held), owner, "owner")
    for key, value in (("start", 0), ("end", 0), ("nonce", "wrong"), ("revision", 2)):
        with pytest.raises(ValueError, match="stale_hold"):
            ops.invoke("cancel", {**held, key: value}, cancel)
    with pytest.raises(SignatureError):
        ops.invoke("cancel", held, "invalid")
    with connect(folder) as db:
        assert db.execute("SELECT count(*) FROM consumed_proofs").fetchone()[0] == 0
    confirmed = ops.invoke(
        "confirm", held, sign_detached(consent_payload(manifest, "confirm", held), owner, "owner")
    )
    confirmed.pop("state")
    assert confirmed["nonce"] != held["nonce"]
    with pytest.raises(ValueError, match="stale_hold"):
        ops.invoke("cancel", held, cancel)
    ops.invoke(
        "cancel",
        confirmed,
        sign_detached(consent_payload(manifest, "cancel", confirmed), owner, "owner"),
    )
    replacement = ops.invoke("hold_slot", base)
    replacement.pop("state")
    assert replacement["id"] != held["id"] and replacement["nonce"] != held["nonce"]
    with pytest.raises(SignatureError):
        ops.invoke("cancel", replacement, cancel)
    assert (
        ops.invoke(
            "cancel",
            replacement,
            sign_detached(consent_payload(manifest, "cancel", replacement), owner, "owner"),
        )["state"]
        == "cancelled"
    )


@pytest.mark.parametrize("config", ["resource"], indirect=True)
def test_slot_grid(tmp_path: Path, config: dict[str, Any]) -> None:
    folder = tmp_path / "artifact"
    generate(
        folder,
        ResourceConfig.model_validate(config),
        Ed25519PrivateKey.generate().public_key(),
        "p1",
    )
    ops = Operations(folder)
    with pytest.raises(ValueError, match="off_grid"):
        ops.invoke("hold_slot", {"start": 541, "end": 571, "prerequisites": []})
    assert (
        ops.invoke("hold_slot", {"start": 540, "end": 570, "prerequisites": []})["state"] == "held"
    )


@pytest.mark.parametrize("config", ["resource"], indirect=True)
def test_concat_disguised_as_video(
    tmp_path: Path,
    media_files: tuple[Path, Path, Path],
    config: dict[str, Any],
) -> None:
    video = media_files[0]
    source = tmp_path / "concat.mp4"
    source.write_text("ffconcat version 1.0\nfile '" + video.as_posix() + "'\n")
    with pytest.raises((ValueError, subprocess.CalledProcessError)):
        extract(source, tmp_path / "bad_frames")
    assert not (tmp_path / "bad_frames").exists()
    assert extract(video, tmp_path / "good_frames")


class PhraseMedia(ScriptedMedia):
    def __init__(self, counts: list[int]) -> None:
        self.counts = counts
        self.phrases: list[str] = []

    async def segment(
        self,
        image: bytes | str,
        phrase: str,
        *,
        coalition_id: str | None = None,
    ) -> tuple[Segment, ...]:
        self.phrases.append(phrase)
        return (Segment(Box(0, 0, 20, 20, 20, 20), "", 0),) * self.counts.pop(0)


@pytest.mark.parametrize(
    "template,counts,phrases,selected",
    [
        ("resource", [0, 1], ["rectangle", "row"], "row"),
        ("device", [17, 0, 1], ["display", "screen", "rectangle"], "rectangle"),
        ("device", [0, 0, 0], ["display", "screen", "rectangle"], "whole_frame"),
        ("resource", [1], ["rectangle"], "rectangle"),
    ],
)
async def test_region_fallback(
    tmp_path: Path,
    template: str,
    counts: list[int],
    phrases: list[str],
    selected: str,
) -> None:
    frame = tmp_path / "frame.png"
    Image.new("RGB", (20, 20)).save(frame)
    media = PhraseMedia(counts)
    fake = FakeModel([ScriptedResponse('{"records":[]}')])
    gateway = ModelGateway(Settings(), transport=fake)
    selections: list[str] = []
    assert await read_frame(frame, media, gateway, "test", template, selections) == []
    assert media.phrases == phrases and selections == [selected]
    assert len(fake.calls) == 1


@pytest.mark.parametrize("config", ["resource"], indirect=True)
async def test_repair_has_reply_and_error(config: dict[str, Any]) -> None:
    fake = FakeModel([ScriptedResponse('{"invalid":1}'), ScriptedResponse(json.dumps(config))])
    gateway = ModelGateway(Settings(), transport=fake)
    await model_config(gateway, "resource", "evidence", "test")
    repair = json.dumps(fake.calls[1])
    assert "invalid" in repair and "Validation error" in repair and "required" in repair


@pytest.mark.parametrize("config", ["device"], indirect=True)
async def test_reader_skips_bad_values(
    tmp_path: Path,
    config: dict[str, Any],
    media_files: tuple[Path, Path, Path],
) -> None:
    folder = tmp_path / "artifact"
    generate(
        folder, DeviceConfig.model_validate(config), Ed25519PrivateKey.generate().public_key(), "p1"
    )
    with connect(folder) as db:
        db.execute("UPDATE lifecycle SET state='approved'")
    records = [
        {"label": "field_1", "value": value, "confidence": 0.99}
        for value in ("bad", "inf", "nan", "42")
    ]
    fake = FakeModel([ScriptedResponse(json.dumps({"records": records}))] * 2)
    gateway = ModelGateway(Settings(), transport=fake)
    for _ in range(2):
        assert await append_frame(folder, media_files[2], ScriptedMedia(), gateway) == 1
    with connect(folder) as db:
        assert db.execute("SELECT count(*) FROM reader_errors").fetchone()[0] == 6
        assert db.execute("SELECT count(*) FROM readings").fetchone()[0] == 2


@pytest.mark.parametrize("config", ["resource"], indirect=True)
def test_grid_uses_containing_window(tmp_path: Path, config: dict[str, Any]) -> None:
    config["windows"] = [{"start": 0, "end": 30}, {"start": 541, "end": 630}]
    folder = tmp_path / "artifact"
    generate(
        folder,
        ResourceConfig.model_validate(config),
        Ed25519PrivateKey.generate().public_key(),
        "p1",
    )
    with pytest.raises(ValueError, match="off_grid"):
        Operations(folder).invoke("hold_slot", {"start": 570, "end": 600, "prerequisites": []})


@pytest.mark.parametrize("config", ["resource"], indirect=True)
def test_prerequisite_attestation_allows_rehold(tmp_path: Path, config: dict[str, Any]) -> None:
    config["prerequisites"] = ["ready"]
    owner = Ed25519PrivateKey.generate()
    folder = tmp_path / "artifact"
    manifest = generate(folder, ResourceConfig.model_validate(config), owner.public_key(), "p1")
    ops = Operations(folder)
    args = {"start": 540, "end": 570, "prerequisites": ["ready"]}
    proof = sign_detached(consent_payload(manifest, "hold_slot", args), owner, "owner")
    ids: set[str] = set()
    for _ in range(2):
        held = ops.invoke("hold_slot", args, proof)
        held.pop("state")
        ids.add(held["id"])
        ops.invoke(
            "cancel", held, sign_detached(consent_payload(manifest, "cancel", held), owner, "owner")
        )
    assert len(ids) == 2
