# SPDX-License-Identifier: Apache-2.0
"""The shape of ``pack.yaml`` (spec: Discipline Pack format)."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from .version import SEMVER, parse_range

Name = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")]
RoleId = Name
SettingKey = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{0,63}$")]
RelPath = Annotated[str, StringConstraints(min_length=1, max_length=256)]
Ability = Literal["charter", "offer", "decide", "decide_own", "commit"]
SchemaKind = Literal["need", "offer", "task", "resource"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RoleSpec(_Strict):
    may: Annotated[list[Ability], Field(min_length=1)]
    label: Annotated[str, StringConstraints(min_length=1, max_length=64)] | None = None


def eval_role(roles: dict[str, RoleSpec], requested: str | None) -> str:
    """Choose a declared eval role, requiring offer and decide for the default."""
    if requested is not None:
        if requested not in roles:
            raise ValueError(f"eval role {requested!r} is not declared")
        return requested
    for name, role in roles.items():
        if {"offer", "decide"} <= set(role.may):
            return name
    raise ValueError("eval participant needs a role; no role has both offer and decide abilities")


class MintEntry(_Strict):
    template: RelPath
    tests: RelPath


class Connector(_Strict):
    name: Name
    command: Annotated[list[str], Field(min_length=1)]


# The built-in strategies a pack may name and the fairness keys each reads (spec, Strategy names).
FAIRNESS_KEYS: dict[str, frozenset[str]] = {
    "auction": frozenset({"weight", "max_ratio", "minute_value"}),
}


class Strategy(_Strict):
    allocation: Name
    fairness: dict[SettingKey, float] | None = None

    @model_validator(mode="after")
    def _known(self) -> Strategy:
        if self.allocation in {"match", "vote"}:
            raise ValueError(f"strategy {self.allocation!r} is reserved for a later version")
        allowed = FAIRNESS_KEYS.get(self.allocation)
        if allowed is None:
            raise ValueError(
                f"strategy {self.allocation!r} is not one of {', '.join(sorted(FAIRNESS_KEYS))}"
            )
        extra = sorted(set(self.fairness or {}) - allowed)
        if extra:
            raise ValueError(f"strategy {self.allocation!r} does not read {', '.join(extra)}")
        fairness = self.fairness or {}
        if "weight" in fairness and not 0 <= fairness["weight"] <= 10:
            raise ValueError("weight must be between 0 and 10")
        if "max_ratio" in fairness and fairness["max_ratio"] <= 0:
            raise ValueError("max_ratio must be greater than 0")
        minute = fairness.get("minute_value")
        if minute is not None and (minute < 1 or minute != int(minute)):
            raise ValueError("minute_value must be a whole number of at least 1")
        return self


Keyword = Annotated[str, StringConstraints(min_length=1, max_length=64, pattern=r"^[^A-Z]+$")]
Example = Annotated[str, StringConstraints(min_length=1, max_length=200)]


class Suggest(_Strict):
    keywords: Annotated[list[Keyword], Field(max_length=50)] = []
    examples: Annotated[list[Example], Field(max_length=50)] = []


class Manifest(_Strict):
    name: Name
    version: str
    core: str
    roles: Annotated[dict[RoleId, RoleSpec], Field(min_length=1)]
    vocabulary: RelPath | None = None
    schemas: dict[SchemaKind, RelPath] | None = None
    policies: list[RelPath] | None = None
    skills: list[RelPath] | None = None
    lessons: list[RelPath] | None = None
    views: RelPath | None = None
    task_templates: RelPath | None = None
    mint: list[MintEntry] | None = None
    connectors: list[Connector] | None = None
    strategy: Strategy | None = None
    suggest: Suggest | None = None
    evals: Annotated[list[RelPath], Field(min_length=1)]
    acceptance: RelPath | None = None

    @field_validator("acceptance")
    @classmethod
    def _acceptance_path(cls, value: str | None) -> str | None:
        from .files import bad_relative_path

        if value is not None and (reason := bad_relative_path(value)):
            raise ValueError(reason)
        return value

    @field_validator("version")
    @classmethod
    def _semver(cls, value: str) -> str:
        if not SEMVER.match(value):
            raise ValueError("version must be semantic, such as 1.0.0")
        return value

    @field_validator("core")
    @classmethod
    def _range(cls, value: str) -> str:
        parse_range(value)
        return value
