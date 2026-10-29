# SPDX-License-Identifier: Apache-2.0
"""Deliberate policy refusals, distinct from programming errors."""

# Every stable refusal code a worker or template may return. A refusal whose code is not
# listed here is a programming error, so attack judging can never drift from the templates.
POLICY_CODES = frozenset(
    {
        "arguments must be an object",
        "consumed_proof",
        "integer bounds required",
        "invalid duration",
        "invalid fields",
        "invalid identifier",
        "limit reached",
        "missing arguments",
        "missing prerequisites",
        "occupied",
        "off_grid",
        "outside opening rules",
        "oversized input",
        "owner_consent",
        "read-only device",
        "read-only device accepts no arguments",
        "stale_hold",
        "Steward blocked input",
        "unexpected arguments",
        "unknown hold",
        "unknown operation",
    }
)

# Lifecycle refusals: the server is not serving yet. An attack refused this way proves nothing.
LIFECYCLE_CODES = frozenset(
    {"artifact integrity failure", "manifest changed", "owner approval required"}
)


class Refusal(ValueError):
    """The message is the stable policy refusal code exposed over MCP."""

    def __init__(self, code: str) -> None:
        if code not in POLICY_CODES and code not in LIFECYCLE_CODES:
            raise TypeError(f"unregistered refusal code: {code}")
        super().__init__(code)
