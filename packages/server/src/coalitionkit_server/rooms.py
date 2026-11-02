# SPDX-License-Identifier: Apache-2.0
"""The rooms a first-time visitor sees on the map.

Discoverable rooms are not stored yet, so this lists only what an operator supplies from a file
(``COALITIONKIT_SAMPLE_ROOMS``) and marks every entry as a sample. Nothing here is ever presented
as a real room, and the kit ships no such file: scenario data stays outside the core.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Literal, Self

from fastapi import Depends, FastAPI, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .adapter import Document

Box = tuple[float, float, float, float]  # lat low, lat high, lon low, lon high
DEFAULT_BOX: Box = (51.4, 51.6, 7.1, 7.4)


class Room(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1, max_length=64)
    goal: str = Field(min_length=1, max_length=140)
    seats: int = Field(ge=1, le=64)
    filled: int = Field(ge=0)
    closes: str = Field(min_length=1, max_length=40)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    status: Literal["forming", "acting"] = "forming"

    @model_validator(mode="after")
    def seats_hold_who_is_seated(self) -> Self:
        if self.filled > self.seats:
            raise ValueError("filled exceeds seats")
        return self


class SampleRooms(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    rooms: tuple[Room, ...] = Field(default=(), max_length=64)
    examples: tuple[str, ...] = Field(default=(), max_length=6)


def load_rooms(path: Path | None) -> Document:
    """Read and check the file once, so a bad one stops the host at start rather than at a visit."""
    samples = (
        SampleRooms.model_validate_json(path.read_text(encoding="utf-8")) if path else SampleRooms()
    )
    return {
        "rooms": [{**room.model_dump(), "sample": True} for room in samples.rooms],
        "examples": list(samples.examples),
    }


def mount_rooms(
    app: FastAPI,
    path: Path | None,
    gate: Callable[[Request], None],
    authorize: Callable[[Request], None],
    extra: Callable[[Box], list[Document]] | None = None,
) -> None:
    listing = load_rooms(path)
    lats, lons = [r["lat"] for r in listing["rooms"]], [r["lon"] for r in listing["rooms"]]
    # Listed rooms spread over the samples' bounds, padded so a single sample still has room.
    box: Box = (
        (min(lats) - 0.05, max(lats) + 0.05, min(lons) - 0.05, max(lons) + 0.05)
        if lats
        else DEFAULT_BOX
    )

    @app.get("/v1/rooms", dependencies=[Depends(gate)])
    async def rooms(request: Request) -> Document:
        authorize(request)
        if extra is None:
            return listing
        return {**listing, "rooms": [*listing["rooms"], *extra(box)]}
