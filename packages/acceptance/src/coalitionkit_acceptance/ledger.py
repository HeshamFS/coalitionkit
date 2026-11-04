# SPDX-License-Identifier: Apache-2.0
"""The ledger of live acceptance usage: every live response, with the UTC time it was collected.

The provider export is per UTC day and per key, so the check needs every live run of a window
merged into one record. A ``StampedMeter`` stamps each response with the UTC time it was metered;
each run appends its responses here in one SQLite transaction (WAL, so processes that run at the
same time lose nothing). A response is marked ``dedicated`` when its run used the dedicated
acceptance key (``COALITIONKIT_META_ACCEPTANCE_KEY``): only those can be matched exactly with an
export filtered to that key. Delete the file to start a new window.
"""

from __future__ import annotations

import os
import sqlite3
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from coalitionkit_models import CostMeter
from coalitionkit_models.meter import BudgetEvent, CostRecord
from coalitionkit_models.prices import PriceTable

LEDGER_VAR = "COALITIONKIT_ACCEPTANCE_LEDGER"
KEY_VAR = "COALITIONKIT_META_ACCEPTANCE_KEY"
DEFAULT = Path.cwd() / ".coalitionkit" / "scorecard-ledger.sqlite3"
SCHEMA = (
    "CREATE TABLE IF NOT EXISTS usage ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT, run TEXT NOT NULL, dedicated INTEGER NOT NULL, "
    "at TEXT NOT NULL, day TEXT NOT NULL, model TEXT NOT NULL, prompt_tokens INTEGER NOT NULL, "
    "cached_tokens INTEGER NOT NULL, completion_tokens INTEGER NOT NULL, "
    "images INTEGER NOT NULL, audio_ms INTEGER NOT NULL, cost_micro_usd INTEGER NOT NULL)"
)
COLUMNS = (
    "run",
    "dedicated",
    "at",
    "day",
    "model",
    "prompt_tokens",
    "cached_tokens",
    "completion_tokens",
    "images",
    "audio_ms",
    "cost_micro_usd",
)


class StampedMeter(CostMeter):
    """A cost meter that remembers the UTC time each response was metered."""

    def __init__(
        self,
        prices: PriceTable,
        on_event: Callable[[BudgetEvent], None] | None = None,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        super().__init__(prices, on_event)
        self._clock = clock
        self.stamps: dict[int, datetime] = {}

    def _add(self, entry: CostRecord) -> CostRecord:  # pyright: ignore[reportIncompatibleMethodOverride]
        self.stamps[id(entry)] = self._clock()
        return super()._add(entry)  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType, reportAttributeAccessIssue]


def dedicated_key_set() -> bool:
    return bool(os.environ.get(KEY_VAR, "").strip())


def ledger_path() -> Path:
    value = os.environ.get(LEDGER_VAR, "").strip()
    return Path(value) if value else DEFAULT


WAL_TRIES = 100


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=60, isolation_level=None)
    connection.execute("PRAGMA busy_timeout=60000")
    # Turning on WAL needs a lock that the busy timeout does not wait for, so two processes
    # starting together can fail here at once. Everything after this line does wait.
    for attempt in range(WAL_TRIES):
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            break
        except sqlite3.OperationalError:
            if attempt == WAL_TRIES - 1:
                connection.close()
                raise
            time.sleep(0.1)
    connection.execute(SCHEMA)
    return connection


def entries(path: Path | None = None) -> list[dict[str, Any]]:
    chosen = path or ledger_path()
    if not chosen.is_file():
        return []
    connection = connect(chosen)
    try:
        rows = connection.execute(f"SELECT {', '.join(COLUMNS)} FROM usage ORDER BY id").fetchall()
    finally:
        connection.close()
    found: list[dict[str, Any]] = [dict(zip(COLUMNS, row, strict=True)) for row in rows]
    for item in found:
        item["dedicated"] = bool(item["dedicated"])
    return found


def record_run(
    run: str,
    meter: CostMeter,
    *,
    path: Path | None = None,
    dedicated: bool | None = None,
) -> int:
    """Append the meter responses in one transaction; each keeps its own UTC stamp."""
    marked = int(dedicated_key_set() if dedicated is None else dedicated)
    stamps: dict[int, datetime] = getattr(meter, "stamps", {})
    now = datetime.now(UTC)
    rows: list[tuple[Any, ...]] = []
    for r in meter.records:
        moment = stamps.get(id(r), now).astimezone(UTC)
        rows.append(
            (
                run,
                marked,
                moment.isoformat(timespec="milliseconds"),
                moment.strftime("%Y-%m-%d"),
                r.model,
                r.prompt_tokens,
                r.cached_tokens,
                r.completion_tokens,
                r.images,
                r.audio_ms,
                r.cost_micro_usd,
            )
        )
    connection = connect(path or ledger_path())
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.executemany(
            f"INSERT INTO usage ({', '.join(COLUMNS)}) VALUES ({', '.join('?' * len(COLUMNS))})",
            rows,
        )
        connection.execute("COMMIT")
    finally:
        connection.close()
    return len(rows)
