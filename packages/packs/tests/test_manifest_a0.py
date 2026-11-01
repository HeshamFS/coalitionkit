# SPDX-License-Identifier: Apache-2.0
"""The pack.yaml keys added for binding: ``suggest`` and validated strategy names."""

import pytest
from pydantic import ValidationError

from coalitionkit_packs.manifest import Manifest

BASE = {
    "name": "pack-test",
    "version": "1.0.0",
    "core": ">=0.1,<0.2",
    "roles": {"member": {"may": ["offer"]}},
    "evals": ["evals/one.yaml"],
}


def test_suggest_keywords_and_examples() -> None:
    manifest = Manifest.model_validate(
        {**BASE, "suggest": {"keywords": ["shared plan"], "examples": ["Agree on one plan"]}}
    )
    assert manifest.suggest is not None
    assert manifest.suggest.keywords == ["shared plan"]


@pytest.mark.parametrize(
    "suggest",
    [
        {"keywords": ["Upper"]},
        {"keywords": [""]},
        {"keywords": ["k"] * 51},
        {"other": []},
    ],
)
def test_suggest_refuses_bad_values(suggest: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Manifest.model_validate({**BASE, "suggest": suggest})


@pytest.mark.parametrize(
    "strategy",
    [
        {"allocation": "auction", "fairness": {"weight": 1, "max_ratio": 2, "minute_value": 1}},
        {"allocation": "match"},
        {"allocation": "vote"},
    ],
)
def test_known_strategies_load(strategy: dict[str, object]) -> None:
    assert Manifest.model_validate({**BASE, "strategy": strategy}).strategy is not None


@pytest.mark.parametrize(
    "strategy",
    [
        {"allocation": "round-robin"},
        {"allocation": "match", "fairness": {"weight": 1}},
        {"allocation": "auction", "fairness": {"share_cap": 0.5}},
        {"allocation": "auction", "fairness": {"weight": 11}},
        {"allocation": "auction", "fairness": {"max_ratio": 0}},
        {"allocation": "auction", "fairness": {"minute_value": 1.5}},
    ],
)
def test_unknown_strategies_or_keys_are_refused(strategy: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Manifest.model_validate({**BASE, "strategy": strategy})
