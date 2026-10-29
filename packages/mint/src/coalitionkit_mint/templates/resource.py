# SPDX-License-Identifier: Apache-2.0
"""Version 1 resource operations inside the caller's SQLite transaction."""

import sqlite3
from typing import Any

from coalitionkit_mint.schema import ResourceConfig


def act(
    db: sqlite3.Connection, config: ResourceConfig, tool: str, args: dict[str, Any]
) -> dict[str, Any]:
    if tool == "list_free_slots":
        if args:
            raise ValueError("unexpected arguments")
        occupied = db.execute("SELECT start, end FROM bookings").fetchall()
        return {
            "slots": [
                {"start": start, "end": start + config.duration}
                for window in config.windows
                for start in range(window.start, window.end - config.duration + 1, config.duration)
                if not any(
                    start < end and start + config.duration > begin for begin, end in occupied
                )
            ]
        }
    if tool == "hold_slot":
        if set(args) != {"id", "start", "end", "prerequisites"}:
            raise ValueError("invalid fields")
        start, end = args["start"], args["end"]
        if type(start) is not int or type(end) is not int or end - start != config.duration:
            raise ValueError("invalid duration")
        if not any(w.start <= start < end <= w.end for w in config.windows):
            raise ValueError("outside opening rules")
        if args["prerequisites"] != config.prerequisites:
            raise ValueError("missing prerequisites")
        if db.execute("SELECT count(*) FROM bookings").fetchone()[0] >= config.limit:
            raise ValueError("limit reached")
        if db.execute(
            "SELECT 1 FROM bookings WHERE start < ? AND end > ?", (end, start)
        ).fetchone():
            raise ValueError("occupied")
        db.execute("INSERT INTO bookings VALUES (?, ?, ?, 'held')", (args["id"], start, end))
        return {"state": "held", "id": args["id"]}
    if tool not in {"confirm", "cancel"} or set(args) != {"id"}:
        raise ValueError("unknown operation")
    if tool == "confirm":
        cursor = db.execute("UPDATE bookings SET state='confirmed' WHERE id=?", (args["id"],))
    else:
        cursor = db.execute("DELETE FROM bookings WHERE id=?", (args["id"],))
    if cursor.rowcount != 1:
        raise ValueError("unknown hold")
    return {"state": "confirmed" if tool == "confirm" else "cancelled"}
