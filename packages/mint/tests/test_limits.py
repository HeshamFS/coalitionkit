# SPDX-License-Identifier: Apache-2.0
"""The Mint's time limits come from the environment, with safe defaults."""

from __future__ import annotations

import pytest

from coalitionkit_mint import limits


def test_defaults_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COALITIONKIT_MINT_TIMEOUT_S", raising=False)
    monkeypatch.delenv("COALITIONKIT_MINT_TOOL_TIMEOUT_S", raising=False)
    assert limits.pipeline_seconds() == 90.0
    assert limits.tool_seconds() == 15.0


def test_values_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COALITIONKIT_MINT_TIMEOUT_S", "240")
    monkeypatch.setenv("COALITIONKIT_MINT_TOOL_TIMEOUT_S", "45.5")
    assert limits.pipeline_seconds() == 240.0
    assert limits.tool_seconds() == 45.5


@pytest.mark.parametrize("bad", ["", "0", "-3", "soon"])
def test_a_bad_value_falls_back(monkeypatch: pytest.MonkeyPatch, bad: str) -> None:
    monkeypatch.setenv("COALITIONKIT_MINT_TIMEOUT_S", bad)
    assert limits.pipeline_seconds() == 90.0
