# SPDX-License-Identifier: Apache-2.0
"""Version 1 device operations: queries only, never a device write."""

import sqlite3
import time
from typing import Any

from coalitionkit_mint.refusal import Refusal
from coalitionkit_mint.schema import DeviceConfig


def act(
    db: sqlite3.Connection, config: DeviceConfig, tool: str, args: dict[str, Any]
) -> dict[str, Any]:
    if args:
        raise Refusal("read-only device accepts no arguments")
    rows = {
        f.id: db.execute(
            "SELECT value, observed FROM readings WHERE field=? ORDER BY rowid DESC LIMIT 1",
            (f.id,),
        ).fetchone()
        for f in config.fields
    }
    if tool == "status":
        fresh = all(
            row and time.time() - row[1] <= 2 * config.interval_seconds for row in rows.values()
        )
        return {"state": "live" if fresh else "stale"}
    if tool == "alarm":
        return {
            "fields": [f.id for f in config.fields if rows[f.id] and rows[f.id][0] > f.threshold]
        }
    for field in config.fields:
        if tool == "read_" + field.id:
            row = rows[field.id]
            return {"value": row[0] if row else None, "observed": row[1] if row else None}
    raise Refusal("read-only device")
