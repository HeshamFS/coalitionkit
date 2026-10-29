# SPDX-License-Identifier: Apache-2.0
"""Canaries: random high-entropy tokens of several shapes, and where each may legitimately be.

A canary is planted in one place (a vault, a redacted field, a private scope, a plan assignment,
a PSI input). The registry records, per canary, the viewers allowed to meet it. Every other
sighting on an outbound surface is a leak.
"""

from __future__ import annotations

import base64
import random
import string
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal
from urllib.parse import quote

Shape = Literal["number", "word", "slot", "document"]
Placement = Literal[
    "vault_fact", "vault_note", "redact", "private_scope", "assignment", "psi_input"
]

#: Pseudo-viewers: the host's own store and reads, and the independent Steward.
HOST = "host"
STEWARD = "steward"


@dataclass(frozen=True)
class Canary:
    """One planted value. ``needle`` is what the scanners look for."""

    cid: str
    shape: Shape
    placement: Placement
    owner: str
    #: What was planted (for a document, the whole sentence; otherwise the needle itself).
    planted: str
    needle: str
    #: Viewers allowed to see it on an outbound surface (participants and pseudo-viewers).
    legit: frozenset[str] = frozenset()
    #: A second planted value that belongs to the first (the end of a slot).
    extra: str = ""

    def variants(self) -> tuple[str, ...]:
        """Encodings a leak could take: plain, case, URL, base64 and hex of the needle."""
        raw = self.needle.encode()
        forms = {
            self.needle,
            self.needle.lower(),
            self.needle.upper(),
            quote(self.needle, safe=""),
            base64.b64encode(raw).decode().rstrip("="),
            base64.urlsafe_b64encode(raw).decode().rstrip("="),
            raw.hex(),
        }
        if self.shape == "slot":
            forms.add(self.needle.replace("T", " "))
        return tuple(sorted(f for f in forms if f))


@dataclass
class Registry:
    """Every canary of one run, with where it was planted."""

    canaries: list[Canary] = field(default_factory=lambda: list[Canary]())

    def add(self, canary: Canary) -> Canary:
        self.canaries.append(canary)
        return canary

    def by_placement(self, placement: Placement) -> list[Canary]:
        return [c for c in self.canaries if c.placement == placement]

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for canary in self.canaries:
            out[canary.placement] = out.get(canary.placement, 0) + 1
        return out


class CanaryFactory:
    """Draws unique canaries from a seeded generator (the runs repeat for a seed)."""

    def __init__(self, rng: random.Random, registry: Registry) -> None:
        self.rng, self.registry = rng, registry
        self._seen: set[str] = set()

    def _unique(self, make: str) -> str:
        if make in self._seen:
            raise ValueError("canary collision")
        self._seen.add(make)
        return make

    def _letters(self, count: int) -> str:
        return "".join(self.rng.choice(string.ascii_lowercase) for _ in range(count))

    def number(self) -> tuple[str, int]:
        value = self.rng.randrange(10**9, 10**10)
        return self._unique(str(value)), value

    def word(self) -> str:
        return self._unique(self._letters(5) + self._letters(9))

    def slot(self) -> tuple[str, str]:
        """A start and an end time on a day no other fixture uses."""
        start = datetime(2060 + self.rng.randrange(30), 1, 1) + timedelta(
            days=self.rng.randrange(365), minutes=5 * self.rng.randrange(1, 280)
        )
        end = start + timedelta(hours=1)
        needle = start.strftime("%Y-%m-%dT%H:%M")
        self._unique(needle)
        return start.strftime("%Y-%m-%dT%H:%M:00Z"), end.strftime("%Y-%m-%dT%H:%M:00Z")

    def document(self) -> tuple[str, str]:
        token = self._unique(
            self._letters(6) + "-" + self._letters(6) + str(self.rng.randrange(1000))
        )
        words = " ".join(self._letters(self.rng.randrange(3, 8)) for _ in range(4))
        return f"memo {token} {words}", token

    def make(
        self,
        shape: Shape,
        placement: Placement,
        owner: str,
        legit: frozenset[str] = frozenset(),
    ) -> Canary:
        """A fresh canary: ``planted`` is the text to place, ``needle`` the key to search for."""
        extra = ""
        if shape == "number":
            needle, _ = self.number()
            planted = needle
        elif shape == "word":
            needle = planted = self.word()
        elif shape == "slot":
            planted, extra = self.slot()
            needle = planted[:16]
        else:
            planted, needle = self.document()
        cid = f"c{len(self.registry.canaries) + 1:02d}"
        return self.registry.add(
            Canary(cid, shape, placement, owner, planted, needle, legit, extra)
        )
