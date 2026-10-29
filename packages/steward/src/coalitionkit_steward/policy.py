# SPDX-License-Identifier: Apache-2.0
"""Load and validate Steward policy YAML in the shape the protocol spec gives.

```yaml
id: no-regulated-advice
applies_to: [coalition.observe, coalition.offer, coalition.propose]
when:
  any_text_matches_category: [medical_dosage, legal_advice, investment_advice]
then: escalate
explain: "Coordinate the task; leave the advice to a qualified person."
```

``when`` holds a closed set of conditions; every condition present must hold (AND), and the
values of a list condition are alternatives (OR). Pack policies may not use ``quarantine``.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from importlib import resources
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    field_validator,
)
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from coalitionkit_contracts import MESSAGE_TYPES

from .categories import CATEGORIES

Action = Literal["allow", "redact", "block", "quarantine", "escalate"]
PACK_ACTIONS: frozenset[str] = frozenset({"allow", "redact", "block", "escalate"})
#: Strictness, lowest first. The strictest matching policy decides.
SEVERITY: dict[str, int] = {"allow": 0, "redact": 1, "escalate": 2, "block": 3, "quarantine": 4}
MAX_PATTERN_LENGTH = 200
MAX_POLICY_BYTES = 64 * 1024

PolicyId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")]


class PolicyError(ValueError):
    """A policy file is invalid. The message says which rule it broke."""


class When(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    any_text_matches_category: list[str] | None = None
    any_text_matches: list[str] | None = None
    addresses_unconsented: bool | None = None
    private_field_in_outbound: bool | None = None
    plan_share_above: Annotated[float, Field(gt=0.0, le=1.0)] | None = None

    @field_validator("any_text_matches_category")
    @classmethod
    def _known_categories(cls, value: list[str] | None) -> list[str] | None:
        unknown = [c for c in value or [] if c not in CATEGORIES]
        if unknown:
            raise ValueError(f"unknown categories {unknown}; known: {sorted(CATEGORIES)}")
        if value is not None and not value:
            raise ValueError("needs at least one category")
        return value

    @field_validator("any_text_matches")
    @classmethod
    def _valid_patterns(cls, value: list[str] | None) -> list[str] | None:
        if value is not None and not value:
            raise ValueError("needs at least one pattern")
        for pattern in value or []:
            if len(pattern) > MAX_PATTERN_LENGTH:
                raise ValueError(f"pattern longer than {MAX_PATTERN_LENGTH} characters")
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ValueError(f"invalid pattern {pattern!r}: {exc}") from exc
        return value

    def model_post_init(self, _context: object) -> None:
        if not any(v is not None for v in self.model_dump().values()):
            raise ValueError("when needs at least one condition")


class Policy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: PolicyId
    applies_to: Annotated[list[str], Field(min_length=1)]
    when: When
    then: Action
    explain: Annotated[str, StringConstraints(min_length=1, max_length=500)]

    @field_validator("applies_to")
    @classmethod
    def _known_types(cls, value: list[str]) -> list[str]:
        unknown = [t for t in value if t not in MESSAGE_TYPES]
        if unknown:
            raise ValueError(f"unknown message types {unknown}")
        return value

    @property
    def severity(self) -> int:
        return SEVERITY[self.then]


def parse_policy(text: str, *, source: Literal["core", "pack"]) -> Policy:
    """Validate one policy document. ``source="pack"`` forbids ``quarantine``."""
    if len(text.encode("utf-8")) > MAX_POLICY_BYTES:
        raise PolicyError("policy file too large")
    try:
        data = YAML(typ="safe", pure=True).load(text)  # pyright: ignore[reportUnknownMemberType]
    except YAMLError as exc:
        raise PolicyError(f"not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise PolicyError("a policy file holds one mapping")
    try:
        policy = Policy.model_validate(data)
    except ValidationError as exc:
        raise PolicyError(_summarise(exc)) from exc
    if source == "pack" and policy.then not in PACK_ACTIONS:
        raise PolicyError(
            f"policy {policy.id}: pack policies may use allow, redact, block or escalate, "
            f"not {policy.then!r} (quarantine acts on a participant and stays with the core)"
        )
    return policy


def _summarise(exc: ValidationError) -> str:
    parts = [f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()]
    return "; ".join(parts)


def load_policy_file(path: Path, *, source: Literal["core", "pack"]) -> Policy:
    try:
        return parse_policy(path.read_text(encoding="utf-8"), source=source)
    except PolicyError as exc:
        raise PolicyError(f"{path.name}: {exc}") from exc


class PolicySet(tuple[Policy, ...]):
    """Policies with unique ids, in a stable order."""

    def __new__(cls, policies: Iterable[Policy]) -> Self:
        items = tuple(policies)
        ids = [p.id for p in items]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            raise PolicyError(f"duplicate policy ids {dupes}")
        return super().__new__(cls, items)

    def get(self, policy_id: str) -> Policy | None:
        return next((p for p in self if p.id == policy_id), None)


def load_policy_dir(directory: Path, *, source: Literal["core", "pack"]) -> PolicySet:
    files = sorted(directory.glob("*.yaml"))
    return PolicySet(load_policy_file(f, source=source) for f in files)


def core_policies() -> PolicySet:
    """The core policies bundled with this package."""
    folder = resources.files("coalitionkit_steward").joinpath("policies", "core")
    names = sorted(p.name for p in folder.iterdir() if p.name.endswith(".yaml"))
    return PolicySet(
        _parse_core(name, folder.joinpath(name).read_text(encoding="utf-8")) for name in names
    )


def _parse_core(name: str, text: str) -> Policy:
    try:
        return parse_policy(text, source="core")
    except PolicyError as exc:
        raise PolicyError(f"{name}: {exc}") from exc
