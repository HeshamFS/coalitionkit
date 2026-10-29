# SPDX-License-Identifier: Apache-2.0
"""Live tests run only with COALITIONKIT_LIVE=1 and COALITIONKIT_META_API_KEY in the environment.

A live run also writes the measured results to ``packages/models/LIVE-RESULTS.md``.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

ROWS_KEY: pytest.StashKey[list[dict[str, object]]] = pytest.StashKey()
RESULTS = Path(__file__).resolve().parent.parent / "LIVE-RESULTS.md"


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    config.stash[ROWS_KEY] = []
    if os.environ.get("COALITIONKIT_LIVE") != "1":
        reason = "live tests off: COALITIONKIT_LIVE is not 1"
    elif not os.environ.get("COALITIONKIT_META_API_KEY", "").strip():
        reason = "no key: COALITIONKIT_META_API_KEY is not set"
    else:
        return
    skip = pytest.mark.skip(reason=reason)
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip)


@pytest.fixture
def live_rows(request: pytest.FixtureRequest) -> list[dict[str, object]]:
    return request.config.stash[ROWS_KEY]


def pytest_sessionfinish(session: pytest.Session) -> None:
    rows = session.config.stash.get(ROWS_KEY, None) or []
    if not rows:
        return
    lines = [
        "# Live results (measured)",
        "",
        "Written by the `live` tests when run with `COALITIONKIT_LIVE=1`. Cost is from the",
        "price table 2026-10-28 applied to the usage the API reported.",
        "",
        "| test | model | latency s | prompt tok | completion tok | reasoning tok "
        "| cost micro-USD | note |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    total = 0
    for r in rows:
        total += int(str(r["cost"]))
        lines.append(
            f"| {r['test']} | {r['model']} | {r['latency']:.2f} | {r['prompt']} | {r['completion']}"
            f" | {r['reasoning']} | {r['cost']} | {r['note']} |"
        )
    lines += ["", f"Total live cost: {total} micro-USD (${total / 1_000_000:.6f})", ""]
    RESULTS.write_text("\n".join(lines), encoding="utf-8", newline="\n")
