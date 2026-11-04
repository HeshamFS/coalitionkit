# SPDX-License-Identifier: Apache-2.0
"""Tool activity: what the agents in a room are doing, as ``coalition.tool`` events.

The host records what it observes, never what a member claims: a hosted agent's model call, a
private set intersection round, a Steward review, an outside agent's MCP tool call or inbound A2A
message. ``record_activity`` takes the activity dict every part of the kit uses::

    {"seat", "agent", "tool", "args", "result", "status", "ms", "refs"}

and writes one host-signed event visible to the whole room. ``args`` and ``result`` are cut to one
line and checked against the deterministic outbound policies first; a line that matches any of
them, or that looks like a key or a token, is recorded as ``withheld``. Callers build both lines
from public facts only (tool names, need titles, counts, event ids), never from a vault.

A recorder failure never reaches the caller: the room's work matters more than its trace.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import re
import time
import weakref
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from coalitionkit_contracts import Scope, is_ulid
from coalitionkit_runtime import Acknowledgement
from coalitionkit_steward.conditions import StewardContext, Subject, evaluate_all

from ..adapter import Document

if TYPE_CHECKING:
    from .engine import RoomEngine

LOG = logging.getLogger(__name__)
LINE = 200
WITHHELD = "withheld"
STATUSES = frozenset({"started", "done", "failed"})
TOOL = re.compile(r"^[a-z0-9_]+:[a-z0-9_.-]+$")
#: Long runs of key-like characters: bearer tokens, API keys, signatures.
SECRET = re.compile(r"[A-Za-z0-9_\-+/=]{40,}")
#: Message types whose Steward review is not recorded: the activity itself, and the private set
#: intersection internals that ``psi:compare`` already stands for.
QUIET_REVIEWS = frozenset(
    {
        "coalition.tool",
        "coalition.query",
        "coalition.answer",
        "coalition.match",
        "coalition.receipt",
        "coalition.projection",
    }
)
_SCOPE = Scope.model_validate({"audience": "coalition"})


@dataclass
class _Open:
    """Started activities not yet finished, and Steward reviews not yet written, per engine."""

    started: dict[tuple[str, str, str], list[str]] = field(default_factory=lambda: {})
    reviews: list[tuple[str, Document]] = field(default_factory=lambda: [])


_STATE: weakref.WeakKeyDictionary[Any, _Open] = weakref.WeakKeyDictionary()


def _open(engine: RoomEngine) -> _Open:
    found = _STATE.get(engine)
    if found is None:
        found = _STATE[engine] = _Open()
    return found


def line(engine: RoomEngine, text: object) -> str:
    """One public line: whitespace folded, at most 200 characters, policies checked."""
    words = " ".join(str(text or "").split())
    if len(words) > LINE:
        words = words[: LINE - 1].rstrip() + "…"
    if not words:
        return ""
    if SECRET.search(words) or _matches_policy(engine, words):
        return WITHHELD
    return words


def _matches_policy(engine: RoomEngine, words: str) -> bool:
    """The deterministic outbound policies, as if the line were said to the whole room."""
    subject = Subject("message", "", "", 1, "coalition.observe", "host", _SCOPE, {"content": words})
    return bool(evaluate_all(engine.policies, subject, StewardContext()))


def clean(engine: RoomEngine, activity: Document) -> Document | None:
    """The contract's dict in its exact shape, or None when it cannot be recorded."""
    tool = str(activity.get("tool", ""))
    status = str(activity.get("status", ""))
    if not TOOL.match(tool) or len(tool) > 64 or status not in STATUSES:
        return None
    raw: list[Any] = list(activity.get("refs") or [])
    refs = [str(r) for r in raw if is_ulid(r)]
    return {
        "seat": str(activity.get("seat") or "host")[:128],
        "agent": str(activity.get("agent") or "host")[:32],
        "tool": tool,
        "args": line(engine, activity.get("args")),
        "result": line(engine, activity.get("result")),
        "status": status,
        "ms": max(0, int(activity.get("ms") or 0)),
        "refs": list(dict.fromkeys(refs))[:32],
    }


def records(engine: RoomEngine, coalition: str) -> bool:
    """Only rooms the engine drives are traced; an operator's own Coalition log is left alone."""
    if coalition not in engine.server.hosts:
        return False
    # A room is driven from its first engine step; before that, Genesis has already made it.
    return coalition in engine.driven or engine.owner(coalition) is not None


async def record_activity(
    engine: RoomEngine, coalition: str, activity: Document, *, start: str | None = None
) -> Document:
    """Record one activity as a ``coalition.tool`` event; ``{}`` when nothing was recorded.

    A finish (``done`` or ``failed``) names its start by ``start``; without it, the oldest open
    start of the same seat and tool is used, so a plain ``on_activity`` callback pairs as well.
    """
    payload = clean(engine, activity)
    if payload is None or not records(engine, coalition):
        return {}
    pending = _open(engine).started
    key = (coalition, payload["seat"], payload["tool"])
    if payload["status"] != "started" and start is None and pending.get(key):
        start = pending[key][0]
    if start is not None and start in pending.get(key, []):
        pending[key].remove(start)
    host = engine.server.hosts[coalition]
    try:
        reply = await engine.thread(
            lambda: host.host_emit("tool", payload, {"audience": "coalition"}, causation_id=start)
        )
    except Exception:
        LOG.exception("Recording %s failed for %s", payload["tool"], coalition)
        return {}
    if not isinstance(reply, Acknowledgement):
        return {}  # the room has ended, or not begun: there is nothing to trace into
    accepted: Document = reply.accepted or {}
    if payload["status"] == "started":
        pending.setdefault(key, []).append(str(accepted["event_id"]))
    return accepted


def reporter(engine: RoomEngine, coalition: str) -> Callable[[Document], Awaitable[None]]:
    """An ``on_activity`` callback bound to one room, for parts that report their own calls."""

    async def on_activity(activity: Document) -> None:
        await record_activity(engine, coalition, activity)

    return on_activity


@dataclass
class Call:
    """What the block inside ``activity`` found: the result line and the events it touched."""

    result: str = "done"
    refs: list[str] = field(default_factory=lambda: [])
    failed: bool = False


@asynccontextmanager
async def activity(
    engine: RoomEngine, coalition: str, seat: str, agent: str, tool: str, args: str
) -> AsyncGenerator[Call]:
    """Record ``started``, time the block, then record ``done`` or ``failed`` with its result."""
    base: Document = {"seat": seat, "agent": agent, "tool": tool, "args": args}
    started = await record_activity(
        engine, coalition, {**base, "result": "", "status": "started", "ms": 0, "refs": []}
    )
    start = started.get("event_id")
    began = time.monotonic()
    call = Call()
    try:
        yield call
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        call.failed, call.result = True, f"failed: {type(exc).__name__}"
        raise
    finally:
        finish: Document = {
            **base,
            "result": call.result,
            "status": "failed" if call.failed else "done",
            "ms": round((time.monotonic() - began) * 1000),
            "refs": call.refs,
        }
        with contextlib.suppress(asyncio.CancelledError):
            await record_activity(engine, coalition, finish, start=start)


# --- Steward reviews ---------------------------------------------------------------------------
def steward_reviewed(engine: RoomEngine, review: Document) -> None:
    """Called by the Steward adapter inside the host's transaction: note it, touch nothing else.

    The engine writes the noted reviews on its next step (``flush_reviews``).
    """
    coalition = str(review.get("coalition", ""))
    if review.get("type") in QUIET_REVIEWS or coalition not in engine.driven:
        return
    _open(engine).reviews.append((coalition, review))
    engine.wake(coalition)


async def flush_reviews(engine: RoomEngine, coalition: str) -> None:
    """Write the Steward reviews noted since the last step, one ``done`` event each."""
    state = _open(engine)
    mine = [r for c, r in state.reviews if c == coalition]
    state.reviews = [(c, r) for c, r in state.reviews if c != coalition]
    for review in mine:
        action = str(review.get("action", "allow"))
        kind = str(review.get("type", "")).removeprefix("coalition.")
        held = action not in {"allow", "redact"}
        result = f"held: {review.get('policy_id') or 'steward'}" if held else action
        await record_activity(
            engine,
            coalition,
            {
                "seat": "host",
                "agent": "steward",
                "tool": "steward:review",
                "args": f"{kind} from {review.get('by', 'host')}",
                "result": result,
                "status": "done",
                "ms": round(float(review.get("seconds", 0)) * 1000),
                "refs": [] if held else [review.get("event_id")],
            },
        )
