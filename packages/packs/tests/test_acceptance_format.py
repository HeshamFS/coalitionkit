# SPDX-License-Identifier: Apache-2.0
"""Strict acceptance format and relative manifest paths."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from coalitionkit_acceptance.pack_acceptance import load_scenario
from coalitionkit_packs import inspect_pack
from coalitionkit_packs.manifest import Manifest
from coalitionkit_packs.sections import AcceptanceScenario

FIXTURE = Path(__file__).parent / "fixtures/pack-delta"


@pytest.mark.parametrize(
    "path", ["../outside.yaml", "/absolute.yaml", "C:/absolute.yaml", "a\\b.yaml"]
)
def test_acceptance_path_confined(path: str) -> None:
    manifest = inspect_pack(FIXTURE).manifest.model_dump()
    manifest["acceptance"] = path
    with pytest.raises(ValidationError):
        Manifest.model_validate(manifest)


@pytest.mark.parametrize("case", ["extra", "member", "role", "case", "count"])
def test_acceptance_format(case: str, tmp_path: Path) -> None:
    pack = inspect_pack(FIXTURE)
    data = load_scenario(pack).model_dump()
    if case == "extra":
        data["expect"]["change"]["extra"] = True
    elif case == "member":
        data["offers"][0]["member"] = "p99"
    elif case == "role":
        # Role membership is checked against the loaded pack by the runner.
        from dataclasses import replace

        roles = pack.manifest.model_copy(update={"roles": {}})
        with pytest.raises(ValueError, match="role"):
            load_scenario(replace(pack, manifest=roles))
        return
    elif case == "case":
        data["expect"]["distinguishing"]["business_holds"] = {"business": 0, "need": 0}
    else:
        data["members"] = data["members"][:1]
    with pytest.raises(ValidationError):
        AcceptanceScenario.model_validate(data)
