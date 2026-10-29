# SPDX-License-Identifier: Apache-2.0
"""Version 1 resource operations inside the caller's SQLite transaction."""

import sqlite3
import uuid
from typing import Any

from coalitionkit_mint.refusal import Refusal
from coalitionkit_mint.schema import ResourceConfig


def act(
    db: sqlite3.Connection, config: ResourceConfig, tool: str, args: dict[str, Any]
) -> dict[str, Any]:
    if tool == "list_free_slots":
        if args:
            raise Refusal("unexpected arguments")
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
        if set(args) != {"start", "end", "prerequisites"}:
            raise Refusal("invalid fields")
        start, end = args["start"], args["end"]
        if type(start) is not int or type(end) is not int or end - start != config.duration:
            raise Refusal("invalid duration")
        if not any(w.start <= start < end <= w.end for w in config.windows):
            raise Refusal("outside opening rules")
        if not any(
            w.start <= start < end <= w.end and (start - w.start) % config.duration == 0
            for w in config.windows
        ):
            raise Refusal("off_grid")
        if args["prerequisites"] != config.prerequisites:
            raise Refusal("missing prerequisites")
        if db.execute(
            "SELECT 1 FROM bookings WHERE start < ? AND end > ?", (end, start)
        ).fetchone():
            raise Refusal("occupied")
        if db.execute("SELECT count(*) FROM bookings").fetchone()[0] >= config.limit:
            raise Refusal("limit reached")
        identifier, nonce = uuid.uuid4().hex, uuid.uuid4().hex
        db.execute(
            "INSERT INTO bookings VALUES (?, ?, ?, 'held', ?, 1)", (identifier, start, end, nonce)
        )
        return {
            "state": "held",
            "id": identifier,
            "start": start,
            "end": end,
            "nonce": nonce,
            "revision": 1,
        }
    if tool not in {"confirm", "cancel"} or set(args) != {
        "id",
        "start",
        "end",
        "nonce",
        "revision",
    }:
        raise Refusal("unknown operation")
    nonce = uuid.uuid4().hex
    if tool == "confirm":
        cursor = db.execute(
            "UPDATE bookings SET state='confirmed', revision=revision+1, nonce=? WHERE id=?",
            (nonce, args["id"]),
        )
    else:
        cursor = db.execute("DELETE FROM bookings WHERE id=?", (args["id"],))
    if cursor.rowcount != 1:
        raise Refusal("unknown hold")
    return {
        **args,
        "nonce": nonce,
        "revision": args["revision"] + 1,
        "state": "confirmed" if tool == "confirm" else "cancelled",
    }
