# SPDX-License-Identifier: Apache-2.0
"""Live tests run only with COALITIONKIT_LIVE=1 and COALITIONKIT_META_API_KEY in the environment.

A live run also writes the measured results as a Markdown table. The path is
``COALITIONKIT_LIVE_RESULTS`` when set, else a file in the system temp folder; the table and the
path are printed at the end of the run. Nothing is written into the repository tree.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

ROWS_KEY: pytest.StashKey[list[dict[str, object]]] = pytest.StashKey()
RESULTS = Path(
    os.environ.get("COALITIONKIT_LIVE_RESULTS")
    or Path(tempfile.gettempdir()) / "coalitionkit-models-live-results.md"
)


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
    text = "\n".join(lines)
    RESULTS.write_text(text, encoding="utf-8", newline="\n")
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is not None:
        reporter.write_line(f"live results written to {RESULTS}")
        reporter.write_line(text)
