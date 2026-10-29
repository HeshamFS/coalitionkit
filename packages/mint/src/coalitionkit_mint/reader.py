# SPDX-License-Identifier: Apache-2.0
"""Trusted edge reader outside the serving process; only appends measured readings."""

import asyncio
import contextlib
import math
import re
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

from coalitionkit_models.gateway import ModelGateway

from .artifact import connect, load
from .perceive import Media, read_frame
from .schema import DeviceConfig


async def append_frame(folder: Path, frame: Path, media: Media, gateway: ModelGateway) -> int:
    config, _, manifest_hash = load(folder)
    if not isinstance(config, DeviceConfig):
        raise ValueError("edge reader requires a device template")
    records = await read_frame(frame, media, gateway, "edge-" + manifest_hash)
    fields = {field.id for field in config.fields}
    # Display labels often contain spaces; template identifiers use underscores.
    labels = {
        record.label: re.sub(r"[^a-z0-9]+", "_", record.label.lower()).strip("_")
        for record in records
    }
    accepted: list[tuple[str, float, float, float]] = []
    errors: list[tuple[str, str, float]] = []
    for record in records:
        if labels[record.label] not in fields or record.confidence < 0.8:
            continue
        try:
            value = float(record.value)
            if not math.isfinite(value):
                raise ValueError("nonfinite reading")
        except ValueError as exc:
            errors.append((labels[record.label], str(exc), time.time()))
            continue
        accepted.append((labels[record.label], value, time.time(), record.confidence))
    with connect(folder) as db:
        if db.execute("SELECT state FROM lifecycle").fetchone()[0] != "approved":
            raise ValueError("reader requires owner approval")
        db.executemany("INSERT INTO reader_errors VALUES (?, ?, ?)", errors)
        db.executemany("INSERT INTO readings VALUES (?, ?, ?, ?)", accepted)
    return len(accepted)


async def run_reader(
    folder: Path,
    capture: Callable[[], Awaitable[Path]],
    media: Media,
    gateway: ModelGateway,
    stop: asyncio.Event,
) -> None:
    config, _, _ = load(folder)
    if not isinstance(config, DeviceConfig):
        raise ValueError("not a device")
    while not stop.is_set():
        await append_frame(folder, await capture(), media, gateway)
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=config.interval_seconds)
