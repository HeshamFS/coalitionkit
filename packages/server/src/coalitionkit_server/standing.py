# SPDX-License-Identifier: Apache-2.0
"""The standing room: a public host keeps one room open from a fixed sentence, on its own clock.

With ``standing_room_goal`` set, the host forms a room from that sentence whenever none is open,
bound to ``standing_room_pack`` and owned by the host's own seat. Visitors join it by its code;
nobody else starts rooms on such a host. The room begins once people have had
``standing_room_gather_minutes`` to arrive (or when it is full), ends itself after
``standing_room_minutes`` with the usual dissolve (vaults erased, lessons written), and a new room
forms on the next step. The owner seat's token is written beside the host key, never served.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import Depends, FastAPI, Request

from .adapter import Document
from .genesis_draft import Draft, Role
from .packs import PackRef

if TYPE_CHECKING:
    from coalitionkit_packs import Pack

    from .app import Server
    from .door import DoorStore

LOG = logging.getLogger(__name__)
TABLE = (
    "CREATE TABLE IF NOT EXISTS server_standing (coalition TEXT PRIMARY KEY, opened TEXT, "
    "ends TEXT, ended INTEGER)"
)
TICK_S = 5.0
OWNER_FILE = "standing-room.json"
OWNER_NAME = "Host"


def standing_on(server: Server) -> bool:
    return bool(server.settings.standing_room_goal)


def seat_roles(pack: Pack | None, seats: int) -> list[Role]:
    """The host's seat takes the pack's chartering role; every other seat takes its first other
    role that may offer. Without a pack every seat is a plain member."""
    if pack is None:
        return [Role(id="member", label="Member", count=seats)]
    roles = pack.manifest.roles
    owner = next((r for r, spec in roles.items() if "charter" in spec.may), next(iter(roles)))
    guest = next((r for r, spec in roles.items() if r != owner and "offer" in spec.may), None)
    first = Role(id=owner, label=roles[owner].label or owner, count=1)
    if guest is None:
        return [first.model_copy(update={"count": seats})]
    return [first, Role(id=guest, label=roles[guest].label or guest, count=seats - 1)]


class StandingRoom:
    def __init__(
        self,
        server: Server,
        doors: DoorStore,
        mutation: asyncio.Lock,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.server = server
        self.doors = doors
        self.mutation = mutation
        self.now = now
        self.task: asyncio.Task[None] | None = None
        with server.store.transaction("") as tx:
            tx.execute(TABLE)

    # --- the clock -------------------------------------------------------------------------
    def start(self) -> None:
        if self.task is None:
            self.task = asyncio.create_task(self.run())

    async def close(self) -> None:
        if self.task is not None:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
            self.task = None

    async def run(self) -> None:
        while True:
            try:
                await self.tick()
            except asyncio.CancelledError:
                raise
            except Exception:  # one bad step must not stop the next room
                LOG.exception("standing room step failed")
            await asyncio.sleep(TICK_S)

    async def tick(self) -> None:
        """One step: end the room whose time is up, tend the open one, or form a new one."""
        current = self.current()
        if current is not None:
            coalition, opened, ends = current
            host = self.server.hosts.get(coalition)
            if host is None or host.state.stage == "Dissolve":
                self.mark_ended(coalition)
            elif self.now() >= ends:
                await self.end(coalition)
            else:
                await self.tend(coalition, opened)
                return
        await self.form()

    # --- reads -----------------------------------------------------------------------------
    def current(self) -> tuple[str, datetime, datetime] | None:
        with self.server.store.transaction("") as tx:
            row = tx.execute(
                "SELECT coalition, opened, ends FROM server_standing WHERE ended = 0 "
                "ORDER BY opened DESC LIMIT 1"
            ).fetchone()
        if not row:
            return None
        return str(row[0]), datetime.fromisoformat(row[1]), datetime.fromisoformat(row[2])

    def pack(self) -> Pack | None:
        name = self.server.settings.standing_room_pack
        if not name:
            return None
        found = [p for (n, _), p in self.server.packs.items() if n == name]
        if not found:
            raise ValueError(f"standing room pack {name} is not installed")
        return max(found, key=lambda p: p.manifest.version)

    def summary(self) -> Document | None:
        """What the landing page shows: the goal, the code and the seats. Never a token."""
        current = self.current()
        if current is None:
            return None
        coalition, _, ends = current
        door = self.doors.view(coalition)
        if door is None:
            return None
        left = max(0.0, (ends - self.now()).total_seconds() / 60)
        bound = self.server.hosts[coalition].state.charter.get("pack")
        meter = self.server.cost_meter(coalition)
        return {
            "goal": door["goal"],
            "code": door["code"],
            "link": door["link"],
            "seats": door["seats"],
            "filled": door["filled"],
            "open": not door["stopped"],
            "ends_at": ends.isoformat(),
            "minutes_left": round(left, 1),
            "pack": bound["name"] if bound else None,
            "budget_usd": self.server.settings.room_budget_usd,
            "spent_usd": round(meter["spent"], 4) if meter else None,
        }

    # --- writes ----------------------------------------------------------------------------
    async def form(self) -> str:
        from .genesis import open_room

        settings = self.server.settings
        goal = settings.standing_room_goal or ""
        pack = self.pack()
        opened = self.now()
        ends = opened + timedelta(minutes=settings.standing_room_minutes)
        draft = Draft(
            goal=goal,
            pack=PackRef(name=pack.name, version=pack.manifest.version) if pack else None,
            roles=seat_roles(pack, settings.standing_room_seats),
            needs=[],
            deadline=ends,
        )
        async with self.mutation:
            made = await open_room(self.server, self.doors, draft, OWNER_NAME, "nearby")
        coalition = str(made["coalition_id"])
        with self.server.store.transaction(coalition) as tx:
            tx.execute(
                "INSERT INTO server_standing VALUES (?, ?, ?, 0)",
                (coalition, opened.isoformat(), ends.isoformat()),
            )
        owner = {
            "coalition_id": coalition,
            **made["owner"],
            "code": made["door"]["code"] if made["door"] else None,
        }
        self.owner_file().write_text(json.dumps(owner), encoding="utf-8")
        LOG.warning("Standing room formed: %s", owner["code"])
        return coalition

    async def tend(self, coalition: str, opened: datetime) -> None:
        """Accept the charter as the host's seat, begin the room when people have had time to
        arrive, and close the host seat's brief: it has no person to answer it."""
        from .room import brief, seats

        engine = self.server.room
        if engine is None:
            return
        owner = engine.owner(coalition)
        state = self.server.hosts[coalition].state
        if owner and not state.accepted_charter(owner):
            # The host is the person behind its own seat: it accepts the charter it wrote.
            await seats.sign_charter(engine, coalition, owner)
            engine.wake(coalition)
            return
        doc = engine.read(coalition)
        if owner and owner in doc["briefs"] and not doc["briefs"][owner]["closed"]:
            brief.close(engine, coalition, owner)
            engine.wake(coalition)
        if doc["begun"] or doc["request"] or doc["needs_state"] != "ready":
            return
        gather = timedelta(minutes=self.server.settings.standing_room_gather_minutes)
        if self.now() - opened < gather or len(seats.people(state, doc)) < 2:
            return
        async with engine.lock_for(coalition):
            try:
                await seats.request_begin(engine, coalition, helpers=False, auto=True)
            except RuntimeError:
                engine.wake(coalition)  # the next step picks up where this stopped

    async def end(self, coalition: str) -> None:
        from .genesis import dissolve_coalition

        async with self.mutation:
            dissolve_coalition(self.server, coalition, "completed")
        self.mark_ended(coalition)

    def mark_ended(self, coalition: str) -> None:
        with self.server.store.transaction(coalition) as tx:
            tx.execute("UPDATE server_standing SET ended = 1 WHERE coalition = ?", (coalition,))
        with contextlib.suppress(OSError):
            self.owner_file().unlink(missing_ok=True)

    def owner_file(self) -> Path:
        return self.server.settings.host_key_file.parent / OWNER_FILE


def mount_standing(
    app: FastAPI,
    server: Server,
    doors: DoorStore,
    gate: Callable[[Request], None],
    mutation: asyncio.Lock,
) -> None:
    """``GET /v1/standing`` for the landing page; the clock starts with the app."""
    standing = (
        StandingRoom(server, doors, mutation)
        if standing_on(server) and server.room is not None
        else None
    )
    app.state.standing = standing

    @app.get("/v1/standing", dependencies=[Depends(gate)])
    async def show() -> Document:  # pyright: ignore[reportUnusedFunction]
        return {"room": standing.summary() if standing else None}
