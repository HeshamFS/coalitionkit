# SPDX-License-Identifier: Apache-2.0
"""Scanners over every outbound surface: what left the host, to whom, and which canaries it held."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal

from .canaries import HOST, STEWARD, Canary, Registry

#: The outbound surfaces of the host, as named in the report.
SURFACES = (
    "log",
    "delivery",
    "ack",
    "receipt",
    "error",
    "view",
    "feed_snapshot",
    "feed_delta",
    "agent_session",
    "a2ui",
    "mcp_tool",
    "mcp_resource",
    "http",
    "steward_verdict",
    "derived",
    "answer",
    "psi_blob",
    "prompt",
    "adversary_guess",
)


def text_of(value: object) -> str:
    """Everything printable in ``value``: JSON for documents, the text itself for strings."""
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


@dataclass(frozen=True)
class Outbound:
    """One thing that left the host: where, for whom, and a label that names the field or event."""

    surface: str
    viewer: str
    label: str
    text: str
    #: For a model prompt: the participant whose agent received it.
    agent_owner: str = ""


@dataclass(frozen=True)
class Leak:
    cid: str
    surface: str
    viewer: str
    label: str
    shape: str
    placement: str

    def describe(self) -> str:
        return (
            f"canary {self.cid} ({self.shape}, planted as {self.placement}) reached surface "
            f"{self.surface} for viewer {self.viewer} at {self.label}"
        )


@dataclass
class Ledger:
    """Everything outbound in one run, in the order it was produced."""

    items: list[Outbound] = field(default_factory=lambda: list[Outbound]())

    def record(
        self, surface: str, viewer: str, label: str, value: object, *, agent_owner: str = ""
    ) -> None:
        if surface not in SURFACES:
            raise ValueError(f"unknown surface {surface}")
        self.items.append(Outbound(surface, viewer, label, text_of(value), agent_owner))


def holds(canary: Canary, text: str) -> bool:
    lowered = text.lower()
    return any(v in text or v.lower() in lowered for v in canary.variants())


#: How one sighting is judged. Only "allowed" is a clean sighting; "steward_model" and
#: "member_agent" are measured and reported on their own; "leak" is a finding.
Judgement = Literal["allowed", "steward_model", "steward_projection", "member_agent", "leak"]


def judge(canary: Canary, item: Outbound) -> Judgement:
    """A canary in a model prompt is allowed only for its owner's own agent.

    A prompt to the Steward model is a separate, explicit category when the Steward may see the
    event the canary rode on (``steward_projection`` when a recipient may see the canary,
    ``steward_model`` when none may); a prompt to the agent of a member the scope entitles is
    another. None of these is an allowed sighting. Any other prompt is a leak.
    """
    if item.surface == "prompt":
        if item.agent_owner == canary.owner:
            return "allowed"
        if item.agent_owner == STEWARD and STEWARD in canary.legit:
            # A recipient other than the owner may see it, so the audit prompt carried a
            # projection that recipient gets. With no such recipient, the prompt carried
            # content nobody was to receive: the PRIV-4 defect.
            others = canary.legit - {HOST, STEWARD, canary.owner}
            return "steward_projection" if others else "steward_model"
        if item.agent_owner in canary.legit and item.agent_owner not in (HOST, STEWARD):
            return "member_agent"
        return "leak"
    return "allowed" if item.viewer in canary.legit else "leak"


@dataclass
class ScanResult:
    leaks: list[Leak] = field(default_factory=lambda: list[Leak]())
    #: Per surface: items scanned, canary sightings by their owner or an allowed viewer.
    scanned: dict[str, int] = field(default_factory=lambda: dict[str, int]())
    sightings: dict[str, int] = field(default_factory=lambda: dict[str, int]())
    leaked: dict[str, int] = field(default_factory=lambda: dict[str, int]())
    #: Canaries sent to a model on purpose: "steward_model" and "member_agent" prompts.
    model_prompts: dict[str, int] = field(default_factory=lambda: dict[str, int]())


def scan(ledger: Ledger, registry: Registry) -> ScanResult:
    result = ScanResult()
    for item in ledger.items:
        result.scanned[item.surface] = result.scanned.get(item.surface, 0) + 1
        for canary in registry.canaries:
            if not holds(canary, item.text):
                continue
            verdict = judge(canary, item)
            if verdict == "allowed":
                result.sightings[item.surface] = result.sightings.get(item.surface, 0) + 1
                continue
            if verdict != "leak":
                result.model_prompts[verdict] = result.model_prompts.get(verdict, 0) + 1
                continue
            result.leaked[item.surface] = result.leaked.get(item.surface, 0) + 1
            result.leaks.append(
                Leak(
                    canary.cid,
                    item.surface,
                    item.viewer,
                    item.label,
                    canary.shape,
                    canary.placement,
                )
            )
    return result


def merge(into: dict[str, int], other: dict[str, int]) -> None:
    for key, count in other.items():
        into[key] = into.get(key, 0) + count


def summary(result: ScanResult) -> dict[str, Any]:
    return {
        "scanned": dict(sorted(result.scanned.items())),
        "sightings_allowed": dict(sorted(result.sightings.items())),
        "leaks": dict(sorted(result.leaked.items())),
        "sent_to_models": dict(sorted(result.model_prompts.items())),
    }
