# SPDX-License-Identifier: Apache-2.0
"""The ``rig`` fixture: a served MCP app on a real localhost port with a FakeHost."""

from __future__ import annotations

from collections.abc import Generator

import pytest

from coalitionkit_mcp.testing_rig import Rig, served_rig


@pytest.fixture
def rig() -> Generator[Rig]:
    with served_rig() as served:
        yield served
