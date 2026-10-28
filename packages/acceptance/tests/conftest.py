# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import pytest

from coalitionkit_acceptance.config import scorecard_path
from coalitionkit_acceptance.metrics import SESSION


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Write the measured values of this session to the path in the environment, if any."""
    path = scorecard_path()
    if path is not None and SESSION.runs:
        SESSION.write(path)
