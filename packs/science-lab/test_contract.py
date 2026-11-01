# SPDX-License-Identifier: Apache-2.0
"""Pack-level checks beyond the fixed acceptance scenario."""

from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

from coalitionkit_contracts import Scope
from coalitionkit_packs import inspect_pack
from coalitionkit_server.packs import suggest_pack
from coalitionkit_steward.conditions import StewardContext, Subject, evaluate_all
from coalitionkit_surfaces import load_catalog

pytestmark = pytest.mark.filterwarnings(
    "ignore:Pack .* schema loaded but not applied at runtime:UserWarning"
)

ROOT = Path(__file__).resolve().parent


def test_genesis_suggests_pack() -> None:
    catalog = load_catalog(ROOT.parents[1] / "spec/catalog/coalitionkit-v0_9.json")
    pack = inspect_pack(ROOT, core_catalog=catalog)
    selected = suggest_pack(
        "Three labs anneal and image samples by Friday.",
        {(pack.name, pack.manifest.version): pack},
    )
    assert selected is not None and selected.name == "science-lab"


@pytest.mark.parametrize(
    ("payload", "policy_id", "action", "paths"),
    [
        ({"ext": {"hazard": "hazardous-shipment"}}, "hazardous-shipment", "escalate", ()),
        ({"content": "Please provide CLINICAL advice"}, "no-clinical-advice", "block", ()),
        ({"content": "dosing"}, "no-clinical-advice", "block", ()),
        ({"content": "cost: 125"}, "redact-lab-cost", "redact", ("payload.content",)),
        ({"content": "125 EUR"}, "redact-lab-cost", "redact", ("payload.content",)),
    ],
)
def test_policy_outcomes(payload, policy_id, action, paths):
    catalog = load_catalog(ROOT.parents[1] / "spec/catalog/coalitionkit-v0_9.json")
    pack = inspect_pack(ROOT, core_catalog=catalog)
    subject = Subject(
        "message",
        "coalition",
        "event",
        1,
        "coalition.offer",
        "p1",
        Scope(audience="coalition"),
        payload,
    )
    matches = evaluate_all(pack.policies, subject, StewardContext())
    assert len(matches) == 1
    assert (matches[0].policy.id, matches[0].policy.then, matches[0].redact) == (
        policy_id,
        action,
        paths,
    )


def test_hazard_cannot_bypass_marker_and_private_fields_are_annotated() -> None:
    import json

    schema = json.loads((ROOT / "schemas/offer.json").read_text())
    validator = Draft202012Validator(schema)
    offer = {
        "instrument": "station-1",
        "sample_capacity": 3,
        "free_window": {"start": "2098-01-03T09:00:00Z", "end": "2098-01-03T17:00:00Z"},
    }
    validator.validate(offer)
    validator.validate({**offer, "hazard": "hazardous-shipment"})
    for value in [True, False, "", "other", None]:
        with pytest.raises(ValidationError):
            validator.validate({**offer, "hazard": value})
    for key in ("cost_ceiling", "internal_priority"):
        assert schema["properties"][key]["x-private"] is True
