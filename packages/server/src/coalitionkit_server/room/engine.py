# SPDX-License-Identifier: Apache-2.0
"""The room engine: makes a hosted room work on its own after the first signature.

One engine per server. ``step`` is level-triggered: it reads where the room stands and does the
next missing thing, so a call that finds nothing to do changes nothing and a restart simply
resumes. The public document (needs, seats added by the host, brief timing, activity) is one row
of ``room_engine``; everything private to a seat lives in that seat's hosted vault under reserved
``_room*`` keys, which dissolve erases with the vault.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import threading
import time
from collections.abc import Awaitable, Callable, Mapping
from copy import deepcopy
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from coalitionkit_contracts import new_ulid
from coalitionkit_surfaces import Catalog, load_catalog

from ..adapter import Document
from ..door import DoorStore

if TYPE_CHECKING:
    from ..app import Server

LOG = logging.getLogger(__name__)
TICK_S = 2.0  # how often an idle room is looked at again (brief deadlines, retries)
ACTIVITY_KEEP = 60
FEED = "_room_feed"
FOR_YOU = "_room_foryou"
RESERVED = "_room"  # vault keys the engine owns; the agent vault routes never show them

TABLE = "CREATE TABLE IF NOT EXISTS room_engine (coalition TEXT PRIMARY KEY, doc TEXT)"


def fresh_doc() -> Document:
    return {
        "needs": [],  # [{id, title, kind, detail}] in the order the Gardener seeded them
        "needs_state": "pending",  # -> "ready" once the Gardener has made them
        "needs_source": "rules",
        "slots": [],  # [{id, label}] shared time slots
        "request": None,  # {helpers, auto, revised, helpers_done} while a begin is under way
        "begun": False,
        "helpers": {},  # participant -> {kind, need_id, label}
        "briefs": {},  # participant -> {opened, closed}; the questions themselves are private
        "briefs_done": False,
        "offers": {},  # participant -> {count}; what was offered is in the log, not here
        "offers_open": None,  # when the offer round began (a person's own agent gets a grace)
        "offers_done": False,
        "gaps_noted": [],  # need ids already announced as having no offer
        "compare": None,  # {state, task_id, queries, answered, took_part, done, slots, compared}
        "plan_notes": {},  # plan id -> {name, line, source}
        "activity": [],
    }


class RoomEngine:
    def __init__(self, server: Server) -> None:
        self.server = server
        self.lock = threading.RLock()
        self.docs: dict[str, Document] = {}
        self.versions: dict[str, int] = {}
        self.ticks: dict[str, int] = {}
        self.cache: dict[tuple[str, str], tuple[tuple[int, int], Document]] = {}
        self.tasks: dict[str, asyncio.Task[None]] = {}
        self.pending: set[asyncio.Future[Any]] = set()
        self.wakes: dict[str, tuple[asyncio.AbstractEventLoop, asyncio.Event]] = {}
        self.locks: dict[str, asyncio.Lock] = {}
        self.now: Callable[[], float] = time.time
        self.catalog: Catalog = load_catalog(server.settings.catalog_file)
        with server.store.transaction("") as tx:
            tx.execute(TABLE)
        self.doors = DoorStore(server)

    # --- wiring -----------------------------------------------------------------------------
    def attach(self, coalition: str) -> None:
        """Count host events, so a cached room state is dropped the moment the log moves."""
        host = self.server.hosts[coalition]
        self.ticks.setdefault(coalition, 0)

        def notify() -> None:
            sub.cursor += 1  # the bus drops a subscriber that falls 1000 events behind
            self.ticks[coalition] += 1
            self.wake(coalition)

        sub = host.bus.subscribe(coalition, since=10**9, notify=notify)

    def ensure(self, coalition: str) -> None:
        """Start this room's background task once. Called from the Gardener loop's step."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        task = self.tasks.get(coalition)
        if task is None or task.done():
            self.wakes[coalition] = (loop, asyncio.Event())
            self.tasks[coalition] = loop.create_task(self.run(coalition))

    def wake(self, coalition: str) -> None:
        pair = self.wakes.get(coalition)
        if pair is not None:
            with contextlib.suppress(RuntimeError):  # the loop has closed; nobody is listening
                pair[0].call_soon_threadsafe(pair[1].set)

    def wake_gardener(self, coalition: str) -> None:
        self.server.gardener.wake(coalition)

    async def close(self) -> None:
        for task in self.tasks.values():
            task.cancel()
        await asyncio.gather(*self.tasks.values(), return_exceptions=True)
        self.tasks.clear()
        # A cancelled step must not leave a store call running past the store's close.
        await asyncio.gather(*self.pending, return_exceptions=True)

    def guard[T](self, work: Awaitable[T]) -> Awaitable[T]:
        """Run store and host work to its end even if the step that awaits it is cancelled."""
        future = asyncio.ensure_future(work)
        self.pending.add(future)
        future.add_done_callback(self.pending.discard)
        future.add_done_callback(lambda f: f.cancelled() or f.exception())
        return asyncio.shield(future)

    def thread[T](self, call: Callable[..., T], *args: Any) -> Awaitable[T]:
        return self.guard(asyncio.to_thread(call, *args))

    async def run(self, coalition: str) -> None:
        host = self.server.hosts[coalition]
        event = self.wakes[coalition][1]
        event.set()
        while host.state.stage != "Dissolve":
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(event.wait(), timeout=TICK_S)
            event.clear()
            try:
                await self.step(coalition)
            except asyncio.CancelledError:
                raise
            except Exception:
                # A failed step is tried again at the next tick; the loop itself never dies.
                LOG.exception("Room engine step failed for %s", coalition)

    def lock_for(self, coalition: str) -> asyncio.Lock:
        return self.locks.setdefault(coalition, asyncio.Lock())

    # --- the step -----------------------------------------------------------------------------
    async def step(self, coalition: str) -> None:
        from . import brief, compare, explain, needs, offers, seats

        host = self.server.hosts[coalition]
        state = await self.thread(lambda: host.state)
        owner = self.owner(coalition)
        if state.stage == "Dissolve" or owner is None or not state.accepted_charter(owner):
            return
        if self.read(coalition)["needs_state"] != "ready":
            await needs.make(self, coalition, state)
            return
        # Only the seat work holds the room lock, so a slow model call never holds up a click
        # on begin; the model steps below run one after another in this task.
        async with self.lock_for(coalition):
            await seats.advance(self, coalition)
        await brief.advance(self, coalition)
        await offers.advance(self, coalition)
        await compare.advance(self, coalition)
        await explain.advance(self, coalition)

    def drives(self, coalition: str) -> bool:
        """Only rooms made through Genesis are driven; others belong to whoever plays them."""
        return self.owner(coalition) is not None

    def effort_objective(self, coalition: str) -> Callable[[Mapping[str, str]], float]:
        """Total effort of a plan, from the public offers: low 1, medium 2, high 3 each."""
        level = {"low": 1, "medium": 2, "high": 3}
        host = self.server.hosts[coalition]
        seen: dict[tuple[str, str], int] = {}
        for offer in host.state.offers.values():
            key = (str(offer["owner"]), str(offer["target"]["id"]))
            seen[key] = min(seen.get(key, 9), level[str(offer["cost"]["effort"])])

        def effort(assignments: Mapping[str, str]) -> float:
            return float(sum(seen.get((who, task), 3) for task, who in assignments.items()))

        return effort

    def needs_ready(self, coalition: str) -> bool:
        with self.lock:
            return bool(self.doc(coalition)["needs_state"] == "ready")

    def may_plan(self, coalition: str) -> bool:
        """A plan waits for the brief, every seat's offers and the time comparison."""
        with self.lock:
            d = self.doc(coalition)
            done = d["compare"] is not None and d["compare"]["state"] == "done"
            return bool(d["begun"] and d["briefs_done"] and d["offers_done"] and done)

    # --- the public document ------------------------------------------------------------------
    def doc(self, coalition: str) -> Document:
        """The live document. Callers that change it go through ``update``."""
        with self.lock:
            if coalition not in self.docs:
                with self.server.store.transaction(coalition) as tx:
                    row = tx.execute(
                        "SELECT doc FROM room_engine WHERE coalition = ?", (coalition,)
                    ).fetchone()
                self.docs[coalition] = json.loads(row[0]) if row else fresh_doc()
            return self.docs[coalition]

    def read(self, coalition: str) -> Document:
        with self.lock:
            return deepcopy(self.doc(coalition))

    def update(self, coalition: str, change: Callable[[Document], None]) -> None:
        with self.lock:
            doc = self.doc(coalition)
            change(doc)
            with self.server.store.transaction(coalition) as tx:
                tx.execute(
                    "INSERT INTO room_engine VALUES (?, ?) "
                    "ON CONFLICT (coalition) DO UPDATE SET doc = excluded.doc",
                    (coalition, json.dumps(doc)),
                )
            self.versions[coalition] = self.versions.get(coalition, 0) + 1

    def bump(self, coalition: str) -> None:
        """Tell the screens something they show has changed, without touching the document."""
        self.versions[coalition] = self.versions.get(coalition, 0) + 1

    def version(self, coalition: str) -> int:
        return self.versions.get(coalition, 0)

    def is_hosted(self, coalition: str, who: str) -> bool:
        with self.server.store.transaction(coalition) as tx:
            row = tx.execute(
                "SELECT hosted FROM server_credentials WHERE coalition = ? AND participant = ?",
                (coalition, who),
            ).fetchone()
        return bool(row and row[0])

    def owner(self, coalition: str) -> str | None:
        with self.server.store.transaction(coalition) as tx:
            row = tx.execute(
                "SELECT participant FROM server_genesis WHERE coalition = ?", (coalition,)
            ).fetchone()
        return str(row[0]) if row else None

    # --- activity -----------------------------------------------------------------------------
    def start_activity(
        self,
        coalition: str,
        verb: str,
        label: str,
        *,
        seat: str | None = None,
        need: str | None = None,
        only: str | None = None,
        source: str = "host",
        state: str = "running",
        event: str | None = None,
    ) -> str:
        """One line of "what is happening". ``only`` limits it to that seat's own screen."""
        entry: Document = {
            "id": new_ulid(),
            "at": datetime.fromtimestamp(self.now(), UTC).isoformat(),
            "seat": seat,
            "verb": verb,
            "need": need,
            "label": label,
            "state": state,
            "ms": None,
            "source": source,
            "event": event,
            "only": only,
        }

        def add(doc: Document) -> None:
            doc["activity"] = [*doc["activity"], entry][-ACTIVITY_KEEP:]

        self.update(coalition, add)
        return str(entry["id"])

    def end_activity(self, coalition: str, entry: str, **fields: Any) -> None:
        def finish(doc: Document) -> None:
            for item in doc["activity"]:
                if item["id"] == entry:
                    item.update(fields)

        self.update(coalition, finish)

    def note(self, coalition: str, verb: str, label: str, **kw: Any) -> None:
        self.start_activity(coalition, verb, label, state="done", **kw)

    def refused_needs(self, coalition: str) -> set[str]:
        """Need ids the host refused when seeding; they will never be events."""
        with self.server.store.transaction(coalition) as tx:
            rows = tx.execute(
                "SELECT id FROM server_genesis_refusals WHERE coalition = ?", (coalition,)
            ).fetchall()
        return {str(r[0]) for r in rows}

    # --- private seat data ----------------------------------------------------------------------
    def vault(self, coalition: str, who: str) -> Document:
        """The seat's reserved record, or {} when it has no hosted vault."""
        try:
            return deepcopy(self.server.registry.vault_values(coalition, who))
        except ValueError:
            return {}

    def feed_add(self, coalition: str, who: str, text: str) -> None:
        """A line in the seat's own feed (what its agent did and said). Never leaves the vault."""
        with self.lock:
            lines = list(self.vault(coalition, who).get(FEED, []))
            at = datetime.fromtimestamp(self.now(), UTC).isoformat()
            self.vault_put(coalition, who, FEED, [*lines, {"at": at, "text": text}][-40:])
        self.bump(coalition)

    def vault_put(self, coalition: str, who: str, key: str, value: Any) -> None:
        if not key.startswith(RESERVED):
            raise ValueError("engine keys start with _room")
        self.server.registry.vault_values(coalition, who, {key: value})
