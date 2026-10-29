# SPDX-License-Identifier: Apache-2.0
"""Scanners over every outbound surface: what left the host, to whom, and which canaries it held."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .canaries import Canary, Registry

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


def allowed(canary: Canary, item: Outbound) -> bool:
    if item.surface == "prompt":
        # A canary in a prompt is fine only when its owner sent it to their own agent, or the
        # prompt went to the Steward and the canary rode on an event the Steward may see.
        return item.agent_owner == canary.owner or item.agent_owner in canary.legit
    return item.viewer in canary.legit


@dataclass
class ScanResult:
    leaks: list[Leak] = field(default_factory=lambda: list[Leak]())
    #: Per surface: items scanned, canary sightings by their owner or an allowed viewer.
    scanned: dict[str, int] = field(default_factory=lambda: dict[str, int]())
    sightings: dict[str, int] = field(default_factory=lambda: dict[str, int]())
    leaked: dict[str, int] = field(default_factory=lambda: dict[str, int]())


def scan(ledger: Ledger, registry: Registry) -> ScanResult:
    result = ScanResult()
    for item in ledger.items:
        result.scanned[item.surface] = result.scanned.get(item.surface, 0) + 1
        for canary in registry.canaries:
            if not holds(canary, item.text):
                continue
            if allowed(canary, item):
                result.sightings[item.surface] = result.sightings.get(item.surface, 0) + 1
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
    }
