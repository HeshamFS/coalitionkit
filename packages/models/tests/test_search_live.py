# SPDX-License-Identifier: Apache-2.0
"""Live web search: the Meta built-in tool and the keyless DuckDuckGo provider.

Runs only with COALITIONKIT_LIVE=1 and COALITIONKIT_META_API_KEY (see conftest.py). The query is
neutral and public. Each test records latency, tokens and cost in the live results table.
"""

from __future__ import annotations

import os
import time

import pytest

from coalitionkit_models import CostMeter, DdgSearch, MetaSearch, Settings, load_price_table

pytestmark = pytest.mark.live
QUERY = "public library with a group study room in Bochum"
CO = "live-search"


def _settings() -> Settings:
    key = os.environ.get("COALITIONKIT_META_API_KEY", "")
    return Settings(_env_file=None, meta_api_key=key)  # pyright: ignore[reportCallIssue]


def _row(rows: list[dict[str, object]], test: str, model: str, started: float, run: object) -> None:
    tokens = getattr(run, "tokens", (0, 0))
    rows.append(
        {
            "test": test,
            "model": model,
            "latency": time.perf_counter() - started,
            "prompt": tokens[0],
            "completion": tokens[1],
            "reasoning": 0,
            "cost": int(getattr(run, "cost_micro_usd", 0)),
            "note": f"{len(getattr(run, 'hits', ()))} hits",
        }
    )


async def test_meta_built_in_search_returns_real_pages(live_rows: list[dict[str, object]]) -> None:
    meter = CostMeter(load_price_table())
    search = MetaSearch(_settings(), meter=meter)
    started = time.perf_counter()
    try:
        run = await search.search(QUERY, limit=4, coalition_id=CO)
    finally:
        await search.aclose()
    _row(live_rows, "meta web_search", "muse-spark-1.3", started, run)
    assert run.hits, "the search returned no page"
    assert all(h.url.startswith(("https://", "http://")) for h in run.hits)
    assert run.queries and run.cost_micro_usd > 0
    assert meter.total(CO) == run.cost_micro_usd


async def test_ddg_search_needs_no_key(live_rows: list[dict[str, object]]) -> None:
    started = time.perf_counter()
    run = await DdgSearch(_settings()).search(QUERY, limit=4)
    _row(live_rows, "ddg search", "ddgs", started, run)
    assert run.hits and all(h.url.startswith(("https://", "http://")) for h in run.hits)
    assert run.cost_micro_usd == 0
