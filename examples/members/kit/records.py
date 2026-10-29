# SPDX-License-Identifier: Apache-2.0
"""What a member records about itself, for the interop scorecard."""

from __future__ import annotations

from dataclasses import dataclass, field

from .brain import ModelUse


@dataclass(frozen=True)
class Sent:
    """One envelope the member put on the wire."""

    type: str
    event_id: str
    valid: bool
    errors: tuple[str, ...]
    outcome: str  # "accepted", a protocol error code, or "transport:<reason>"
    latency_s: float


@dataclass(frozen=True)
class Turn:
    """One delivery handled (and, when a model ran, the model turn inside it)."""

    kind: str
    latency_s: float
    model_s: float = 0.0
    model_calls: int = 0


@dataclass
class MemberLog:
    sent: list[Sent] = field(default_factory=lambda: [])
    turns: list[Turn] = field(default_factory=lambda: [])
    uses: list[ModelUse] = field(default_factory=lambda: [])
    received: int = 0
    received_invalid: int = 0
    unverified_peer_originals: int = 0
    prompts: list[str] = field(default_factory=lambda: [])
    turn_errors: list[str] = field(default_factory=lambda: [])
    dissolved: str | None = None

    def refusals(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in self.sent:
            if item.outcome != "accepted":
                counts[item.outcome] = counts.get(item.outcome, 0) + 1
        return counts
