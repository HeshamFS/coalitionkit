# SPDX-License-Identifier: Apache-2.0
"""Environment switches for the acceptance runs. Every default is the small PR-time variant."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

FULL_VAR = "COALITIONKIT_ACCEPTANCE_FULL"
SCORECARD_VAR = "COALITIONKIT_ACCEPTANCE_SCORECARD"
DATABASE_VAR = "COALITIONKIT_TEST_DATABASE_URL"
USAGE_VAR = "COALITIONKIT_ACCEPTANCE_USAGE_FILE"


@dataclass(frozen=True)
class ScaleSize:
    """One scale run: one big Coalition, and many small ones at once."""

    big_agents: int
    coalitions: int
    coalition_agents: int
    tasks: int
    workers: int


PR_SIZE = ScaleSize(big_agents=50, coalitions=10, coalition_agents=10, tasks=3, workers=8)
FULL_SIZE = ScaleSize(big_agents=200, coalitions=50, coalition_agents=10, tasks=4, workers=10)


def full_run() -> bool:
    return os.environ.get(FULL_VAR, "") == "1"


def scale_size() -> ScaleSize:
    return FULL_SIZE if full_run() else PR_SIZE


def scorecard_path() -> Path | None:
    value = os.environ.get(SCORECARD_VAR, "").strip()
    return Path(value) if value else None


def database_url() -> str | None:
    value = os.environ.get(DATABASE_VAR, "").strip()
    return value or None


def usage_file(default: Path) -> Path:
    """The provider usage export to compare the meter with; the recorded fixture by default."""
    value = os.environ.get(USAGE_VAR, "").strip()
    return Path(value) if value else default
