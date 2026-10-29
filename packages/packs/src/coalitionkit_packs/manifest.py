# SPDX-License-Identifier: Apache-2.0
"""The shape of ``pack.yaml`` (spec: Discipline Pack format)."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

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


class MintEntry(_Strict):
    template: RelPath
    tests: RelPath


class Connector(_Strict):
    name: Name
    command: Annotated[list[str], Field(min_length=1)]


class Strategy(_Strict):
    allocation: Name
    fairness: dict[SettingKey, float] | None = None


class Manifest(_Strict):
    name: Name
    version: str
    core: str
    roles: Annotated[dict[RoleId, RoleSpec], Field(min_length=1)]
    vocabulary: RelPath | None = None
    schemas: dict[SchemaKind, RelPath] | None = None
    policies: list[RelPath] | None = None
    skills: list[RelPath] | None = None
    views: RelPath | None = None
    task_templates: RelPath | None = None
    mint: list[MintEntry] | None = None
    connectors: list[Connector] | None = None
    strategy: Strategy | None = None
    evals: Annotated[list[RelPath], Field(min_length=1)]

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
