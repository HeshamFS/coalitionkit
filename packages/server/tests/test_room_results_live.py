# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
"""Live: a real room whose goal asks for a list, a budget and a poster, with the real models.

Reads COALITIONKIT_META_API_KEY (and COALITIONKIT_BASETEN_API_KEY for the Steward) from the
environment only, and skips with the reason "no key" without it. Run with ``-s``: each test
prints one ``OUTCOME`` line with timings, tokens and cost.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any

import pytest
from room_rig import bearer, events, until
from test_room_live import KEY, Run, live_client, results_of

from coalitionkit_models import CostMeter, load_price_table
from coalitionkit_models.media import MediaClient, image_mime
from coalitionkit_models.settings import Settings as ModelSettings
from coalitionkit_server.room import image, media_store

pytestmark = pytest.mark.live

GOAL = (
    "Two of us need to organise a small get-together: a shared list of what to bring, "
    "a budget of 120 euro, and a poster for the door"
)


@pytest.mark.skipif(not KEY, reason="no key")
def test_live_the_image_model_draws_from_a_public_prompt() -> None:
    meter = CostMeter(load_price_table())
    client = MediaClient(ModelSettings(), meter=meter)
    facts = {"goal": GOAL, "need": {"title": "Make a poster", "detail": "For the door."}}
    prompt = image.prompt_for(facts)
    started = time.monotonic()

    async def draw() -> bytes:
        try:
            return await client.generate_image(prompt, image.SIZE, coalition_id="live")
        finally:
            await client.aclose()

    data = asyncio.run(draw())
    ms = round((time.monotonic() - started) * 1000)
    (Path(os.environ.get("RESULTS_LIVE_OUT", ".")) / "live-poster.bin").write_bytes(data)
    size = media_store.size_of(data)
    print(
        "OUTCOME "
        + json.dumps(
            {
                "ms": ms,
                "bytes": len(data),
                "mime": image_mime(data),
                "size": size,
                "cost_usd": meter.total("live") / 1e6,
                "prompt": prompt,
            }
        )
    )
    assert image_mime(data).startswith("image/") and size is not None


@pytest.mark.skipif(not KEY, reason="no key")
def test_live_a_room_lays_out_a_budget_a_list_and_a_poster(tmp_path: Path) -> None:
    with live_client(tmp_path) as client:
        run = Run(client, os.environ.get("ROOM_LIVE_GOAL_TEXT") or GOAL)
        run.to_plans()
        run.decide_and_commit()
        run.mark("committed")
        kinds = {n["kind"] for n in run.engine.read(run.cid)["needs"]}
        until(lambda: len(results_of(client, run.cid)) >= len(kinds), 420, "results")
        run.mark("results")
        made = [json.loads(e["payload"]["content"]) for e in results_of(client, run.cid)]
        parts = {m["kind"]: sorted({n["component"] for n in m["components"]}) for m in made}
        picture = next((m for m in made if m["kind"] == "image"), None)
        served = None
        if picture and picture["data"].get("hash"):
            token = bearer(run.room["owner"]["token"])
            got = client.get(f"/v1/room/media/{picture['data']['hash']}", headers=token)
            served = [got.status_code, got.headers.get("content-type"), len(got.content)]
        extra: dict[str, Any] = {
            "needs": [(n["title"], n["kind"]) for n in run.engine.read(run.cid)["needs"]],
            "parts": parts,
            "sources": {m["kind"]: m["source"] for m in made},
            "picture": picture
            and {k: picture["data"].get(k) for k in ("alt", "prompt", "width", "height", "why")},
            "served": served,
            "results": len(events(client, run.cid, "observe")),
        }
        run.report("results", extra)
        assert "image" in kinds and picture is not None and served and served[0] == 200
        if "budget" in parts:
            assert "CostSplit" in parts["budget"]
        if "list" in parts:
            assert "Checklist" in parts["list"]
