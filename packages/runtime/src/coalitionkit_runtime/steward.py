# SPDX-License-Identifier: Apache-2.0
"""Steward verdicts contain policy metadata, never forwarded source content."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from .store import Document


@dataclass(frozen=True)
class Verdict:
    action: Literal["allow", "redact", "block", "quarantine", "escalate"] = "allow"
    policy_id: str = "default"
    redact: tuple[str, ...] = ()


class Steward(Protocol):
    def review(self, envelope: Document) -> Verdict: ...


class FakeSteward:
    def __init__(self, verdict: Verdict | None = None) -> None:
        self.verdict = verdict or Verdict()
        self.calls: list[str] = []

    def review(self, envelope: Document) -> Verdict:
        self.calls.append(envelope["event_id"])
        return self.verdict
