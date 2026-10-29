# SPDX-License-Identifier: Apache-2.0
"""Acceptance-test hook: off unless ``COALITIONKIT_TEST_HOOK_DIR`` names a directory.

When on, the server appends one JSON line per acceptance boundary to ``<dir>/boundaries.jsonl``:
``received`` (the envelope reached the host, nothing stored yet) and ``persisted`` (the event is
stored and the reply has not been sent). Each line has the event ID, the stage, the participant and
a ``time.perf_counter()`` reading (one clock for every process on the machine). For ``persisted``
the reading is the moment the event was published on the bus, the first instant a viewer can learn
of it, so a viewer delta can never precede it. When
``COALITIONKIT_TEST_HOOK_PAUSE`` is ``<stage>:<participant>``, the server hangs at that stage for
that participant's envelopes, so a harness can kill it at a defined point.
"""

import asyncio
import json
import os
import time
from pathlib import Path
from threading import Lock
from typing import Any

DIR_VAR = "COALITIONKIT_TEST_HOOK_DIR"
PAUSE_VAR = "COALITIONKIT_TEST_HOOK_PAUSE"
FILE = "boundaries.jsonl"
_LOCK = Lock()
_PUBLISHED: dict[tuple[str, int], float] = {}


def watch(bus: Any) -> None:
    """Stamp each publication on ``bus`` (when the hook is on) before subscribers are woken."""
    original = bus.publish

    def publish(coalition_id: str, seq: int) -> None:
        if os.environ.get(DIR_VAR):
            _PUBLISHED[(coalition_id, seq)] = time.perf_counter()
        original(coalition_id, seq)

    bus.publish = publish


async def reached(stage: str, envelope: dict[str, Any], seq: int | None = None) -> None:
    directory = os.environ.get(DIR_VAR)
    if not directory:
        return
    participant = str(envelope.get("on_behalf_of", ""))
    key = (str(envelope.get("coalition_id", "")), seq or 0)
    stamp = _PUBLISHED.pop(key, None) if stage == "persisted" else None
    line = json.dumps(
        {
            "event_id": envelope.get("event_id"),
            "stage": stage,
            "participant": participant,
            "t": stamp if stamp is not None else time.perf_counter(),
        }
    )
    with _LOCK, (Path(directory) / FILE).open("a", encoding="utf-8") as stream:
        stream.write(line + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    if os.environ.get(PAUSE_VAR) == f"{stage}:{participant}":
        await asyncio.Event().wait()  # hang until the harness kills this process
