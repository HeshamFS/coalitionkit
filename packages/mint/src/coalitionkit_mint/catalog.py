# SPDX-License-Identifier: Apache-2.0
"""Plain data for the existing Mint family; no renderer or component definitions."""

import time
from pathlib import Path
from typing import Any

from .artifact import connect
from .schema import Config, DeviceConfig


def twin_data(folder: Path, config: Config, artifact_id: str) -> dict[str, Any]:
    data: dict[str, Any] = {
        "CaptureCard": {
            "masks": [],
            "narration": artifact_id + "-voice",
            "tips": [],
            "video": artifact_id + "-video",
        },
    }
    with connect(folder) as db:
        if not isinstance(config, DeviceConfig):
            bookings = [
                {"start": row[0], "end": row[1]}
                for row in db.execute("SELECT start, end FROM bookings ORDER BY start")
            ]
            data["ScheduleTwin"] = {
                "machines": [{"name": config.name, "owner": "owner", "bookings": bookings}]
            }
            return data
        series = [
            {"field": row[0], "value": row[1], "t": row[2], "confidence": row[3]}
            for row in db.execute(
                "SELECT field, value, observed, confidence FROM readings ORDER BY rowid"
            )
        ]
    latest = {item["field"]: item for item in series}
    data["DeviceReading"] = {
        "annotations": [],
        "limits": [f.model_dump() for f in config.fields],
        "planned": [],
        "series": series,
        "source": artifact_id,
        "unit": config.fields[0].unit,
    }
    data["DeviceAlarm"] = [
        {
            "autoAction": "none",
            "device": artifact_id,
            "duration": max(0.0, time.time() - latest[f.id]["t"]),
            "reading": latest[f.id]["value"],
            "threshold": f.threshold,
        }
        for f in config.fields
        if f.id in latest and latest[f.id]["value"] > f.threshold
    ]
    data["EdgeReaderStatus"] = {
        "confidence": min((r["confidence"] for r in latest.values()), default=0.0),
        "fallback": "mark stale when frames stop",
        "framesKept": "none",
        "rate": 1 / config.interval_seconds,
        "source": "camera",
    }
    return data
