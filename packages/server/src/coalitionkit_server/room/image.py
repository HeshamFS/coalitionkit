# SPDX-License-Identifier: Apache-2.0
"""The ``image`` result: a picture a need asks for (a poster, a card, a menu), drawn by a model.

The prompt is built by code from the room's public facts only: the goal, the need's title and
its detail. No vault value, answer or name is in it. Before anything leaves the host the prompt
passes the Steward's deterministic outbound policies as if it were a message to the whole room;
a match holds the call. The picture is kept on the host keyed by its SHA-256 (``media_store``)
and the result's data is ``{hash, alt, prompt, width, height}``. Without a key, or when the call
fails, the data says why and keeps the prompt, so the group can still use it.
"""

from __future__ import annotations

import asyncio
import contextlib
import re
import time
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from coalitionkit_contracts import Scope, new_ulid
from coalitionkit_models import MissingKeyError
from coalitionkit_models.media import MediaClient
from coalitionkit_steward.conditions import StewardContext, Subject, evaluate_all

from ..adapter import Document
from . import media_store
from .needs import tidy

if TYPE_CHECKING:
    from .engine import RoomEngine

Activity = Callable[[Document], Awaitable[None]]
IMAGE_TIMEOUT_S = 120.0
SIZE = "1024x1024"
PROMPT_MAX = 700
THINGS = re.compile(
    r"\b(poster|flyer|invitation card|invitation|greeting card|card|menu|banner|sign|"
    r"picture|image|illustration|drawing)s?\b",
    re.I,
)
STYLE = (
    "Friendly flat illustration, warm colours, clear shapes, plenty of empty space. "
    "No text, letters, numbers, logos or real people's faces."
)


def thing_of(facts: Document) -> str:
    """What sort of picture the need asks for, in its own word ("poster" when it says none)."""
    need = facts["need"]
    for text in (need["title"], need["detail"], facts["goal"]):
        found = THINGS.search(str(text))
        if found:
            return found[1].lower()
    return "poster"


def prompt_for(facts: Document) -> str:
    """The words sent to the image model: public facts of the room, never a vault value."""
    need = facts["need"]
    detail = tidy(str(need["detail"]), 200)
    detail = "" if detail.lower().startswith("taken from the goal") else detail
    text = (
        f"A {thing_of(facts)} for a small group. It is for: {tidy(str(need['title']), 120)}. "
        f"{detail} The occasion: {tidy(str(facts['goal']), 240)}. {STYLE}"
    )
    return tidy(re.sub(r"\s+", " ", text), PROMPT_MAX)


def held_by(engine: RoomEngine, coalition: str, who: str, text: str) -> str | None:
    """The id of the first deterministic policy that stops this text leaving the host, if any."""
    subject = Subject(
        "message",
        coalition,
        new_ulid(),
        1,
        "coalition.observe",
        who,
        Scope(audience="coalition"),
        {"source": "document", "content": text},
    )
    for match in evaluate_all(engine.policies, subject, StewardContext()):
        if match.policy.then != "allow":
            return match.policy.id
    return None


def media_client(engine: RoomEngine) -> Any:
    """The host's media client, made once from the gateway's settings and cost meter."""
    client = getattr(engine.server, "media", None)
    if client is None:
        gateway = engine.server.gateway
        client = MediaClient(gateway.settings, meter=gateway.meter)
        engine.server.media = client  # pyright: ignore[reportAttributeAccessIssue]
    return client


def activity_sink(engine: RoomEngine, coalition: str) -> Activity | None:
    """The room's tool-activity recorder, bound to this room; None for a room that is not traced."""
    from .activity import records, reporter

    return reporter(engine, coalition) if records(engine, coalition) else None


def spent(engine: RoomEngine, coalition: str) -> int:
    meter = engine.server.gateway.meter
    return meter.total(coalition) if meter is not None else 0


async def report(on_activity: Activity | None, activity: Document) -> None:
    if on_activity is not None:
        # A broken recorder never stops the picture.
        with contextlib.suppress(Exception):
            await on_activity(activity)


async def draw(
    engine: RoomEngine, coalition: str, who: str, prompt: str
) -> tuple[bytes | None, str]:
    """The picture's bytes, or None and why not, in words a person can read."""
    try:
        async with asyncio.timeout(IMAGE_TIMEOUT_S):
            data = await media_client(engine).generate_image(
                prompt, SIZE, coalition_id=coalition, participant=who
            )
    except MissingKeyError:
        return None, "No image model is set up on this host."
    except Exception as exc:  # any failure: the result says so and keeps the prompt
        return None, f"The image model did not answer ({type(exc).__name__})."
    return data, ""


async def make_image(
    engine: RoomEngine,
    coalition: str,
    who: str,
    task: str,
    facts: Document,
    on_activity: Activity | None = None,
) -> tuple[Document, str]:
    """(data, source): the picture's data and "model", or what stopped it and "rules"."""
    prompt = prompt_for(facts)
    alt = tidy(str(facts["need"]["title"]), 140)
    base: Document = {"hash": None, "alt": alt, "prompt": prompt}
    policy = held_by(engine, coalition, who, prompt)
    if policy is not None:
        engine.record_stop(coalition, who, None, policy)
        return {**base, "why": "The Steward held the picture's words, so none was drawn."}, "rules"
    entry = engine.start_activity(
        coalition, "making", f"Drawing {alt}", seat=who, need=task, source="model"
    )
    line = tidy(prompt, 120)

    def tool(status: str, result: str, ms: int) -> Document:
        return {
            "seat": who,
            "agent": "hosted",
            "tool": "media:image",
            "args": line,
            "result": result,
            "status": status,
            "ms": ms,
            "refs": [],
        }

    await report(on_activity, tool("started", "", 0))
    started, before = time.monotonic(), spent(engine, coalition)
    data, why = await draw(engine, coalition, who, prompt)
    ms = round((time.monotonic() - started) * 1000)
    cost = spent(engine, coalition) - before
    digest = ""
    if data is not None:
        try:
            digest = media_store.save(engine.server, coalition, data)
        except (OSError, ValueError):
            data, why = None, "The picture could not be kept on the host."
    if data is None:
        engine.end_activity(coalition, entry, state="failed", ms=ms, source="rules", error=why)
        await report(on_activity, tool("failed", why, ms))
        return {**base, "why": why}, "rules"
    width, height = media_store.size_of(data) or (1024, 1024)
    engine.end_activity(coalition, entry, state="done", ms=ms, source="model", cost=cost)
    await report(on_activity, tool("done", f"{width}x{height} picture {digest[:12]}", ms))
    return {**base, "hash": digest, "width": width, "height": height}, "model"
