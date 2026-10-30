# SPDX-License-Identifier: Apache-2.0
"""Closed, bounded inputs to the two versioned templates."""

import itertools
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Identifier = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{0,47}$")]
Text = Annotated[str, StringConstraints(min_length=1, max_length=200)]
Minute = Annotated[int, Field(ge=0, le=1440)]


class Closed(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class Window(Closed):
    start: Minute
    end: Minute

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.start >= self.end:
            raise ValueError("empty window")
        return self


class ResourceConfig(Closed):
    template: Literal["resource"]
    name: Text
    windows: Annotated[list[Window], Field(min_length=1, max_length=32)]
    duration: Annotated[int, Field(ge=1, le=1440)]
    limit: Annotated[int, Field(ge=1, le=100)]
    prerequisites: Annotated[list[Identifier], Field(max_length=16)]

    @model_validator(mode="after")
    def usable(self) -> Self:
        ordered = sorted(self.windows, key=lambda w: w.start)
        if any(a.end > b.start for a, b in itertools.pairwise(ordered)):
            raise ValueError("overlapping windows")
        if not any(w.end - w.start >= self.duration for w in ordered):
            raise ValueError("no slot fits")
        return self


class DisplayField(Closed):
    id: Identifier
    unit: Text
    threshold: Annotated[float, Field(allow_inf_nan=False)]


class DeviceConfig(Closed):
    template: Literal["device"]
    name: Text
    fields: Annotated[list[DisplayField], Field(min_length=1, max_length=16)]
    interval_seconds: Annotated[int, Field(ge=1, le=3600)]

    @model_validator(mode="after")
    def unique(self) -> Self:
        if len({f.id for f in self.fields}) != len(self.fields):
            raise ValueError("duplicate field")
        return self


Config = ResourceConfig | DeviceConfig


def parse_config(text: str) -> Config:
    from pydantic import TypeAdapter

    return TypeAdapter(Config).validate_json(text)


class Record(Closed):
    label: Text
    value: Text
    confidence: Annotated[float, Field(ge=0, le=1)]


class Observations(Closed):
    records: Annotated[list[Record], Field(max_length=64)]


class Attack(Closed):
    tool: Identifier
    arguments_json: Annotated[str, StringConstraints(max_length=8000)]


class Attacks(Closed):
    cases: Annotated[list[Attack], Field(min_length=1, max_length=16)]
