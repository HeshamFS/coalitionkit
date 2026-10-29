# SPDX-License-Identifier: Apache-2.0
"""Deliberate policy refusals, distinct from programming errors."""


class Refusal(ValueError):
    """The message is the stable policy refusal code exposed over MCP."""
