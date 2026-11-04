# SPDX-License-Identifier: Apache-2.0
"""The Door: a many-use short code, live seats, and knocks from strangers.

Every admission here still ends in a one-use invitation redeemed by ``coalition.join`` (spec:
Admission by short code and knock). A short code never names a member; a knock is answered by
the opener, and a yes hands the knocker one invitation, once.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from collections import deque
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, Literal

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from coalitionkit_contracts import new_ulid, public_key_to_jwk
from coalitionkit_edges.a2a.identity import CardError

from .adapter import Document
from .rooms import Box
from .whatsapp import viewer_key
from .whatsapp_store import TABLES as WHATSAPP_TABLES

if TYPE_CHECKING:
    import asyncio

    from .app import Server

CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
START_PER_MINUTE = 10
JOIN_PER_CODE = 30
JOIN_PER_CALLER = 10
KNOCK_PER_CALLER = 5
KNOCK_POLL_PER_CALLER = 60
KNOCKS_OPEN_MAX = 20
KNOCK_LIFETIME = timedelta(minutes=15)
WINDOW_S = 60.0

TABLES = (
    "CREATE TABLE IF NOT EXISTS server_doors (coalition TEXT PRIMARY KEY, code TEXT UNIQUE, "
    "room TEXT UNIQUE, visibility TEXT, goal TEXT, place TEXT, closes_at TEXT, "
    "stopped INTEGER, roles TEXT)",
    "CREATE TABLE IF NOT EXISTS server_door_arrivals (coalition TEXT, participant TEXT, "
    "role TEXT, at TEXT, n INTEGER, PRIMARY KEY (coalition, participant))",
    "CREATE TABLE IF NOT EXISTS server_door_knocks (id TEXT PRIMARY KEY, coalition TEXT, "
    "secret TEXT, state TEXT, invitation TEXT, at TEXT)",
)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class Limiter:
    """A sliding-minute counter held in memory, one per host process."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.hits: dict[str, deque[float]] = {}

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        if len(self.hits) > 10000:
            self.hits = {k: v for k, v in self.hits.items() if v and v[-1] > now - WINDOW_S}
        window = self.hits.setdefault(key, deque())
        while window and window[0] <= now - WINDOW_S:
            window.popleft()
        if len(window) >= self.limit:
            return False
        window.append(now)
        return True


def caller(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def new_code() -> str:
    pick = "".join(secrets.choice(CODE_ALPHABET) for _ in range(7))
    return pick[:3] + "-" + pick[3:]


def clean_code(raw: str) -> str | None:
    code = raw.strip().upper()
    ok = len(code) == 8 and code[3] == "-" and all(c in CODE_ALPHABET for c in code[:3] + code[4:])
    return code if ok else None


def position(room: str, box: Box) -> tuple[float, float]:
    """A stable point inside the box derived from the room's id; rooms hold no coordinates yet."""
    raw = hashlib.sha256(room.encode()).digest()
    u, v = (int.from_bytes(raw[i : i + 4], "big") / 2**32 for i in (0, 4))
    return round(box[0] + u * (box[1] - box[0]), 5), round(box[2] + v * (box[3] - box[2]), 5)


def knocks_since() -> str:
    """A knock nobody answered lapses, so it can neither hold the queue nor wait for ever."""
    return (datetime.now(UTC) - KNOCK_LIFETIME).isoformat()


def erase_door(tx: Any, coalition: str) -> int:
    """Every door, knock and arrival row of one coalition; returns how many went."""
    total = 0
    for table in ("server_doors", "server_door_arrivals", "server_door_knocks", "server_names"):
        gone = tx.execute(f"DELETE FROM {table} WHERE coalition = ? RETURNING 1", (coalition,))
        total += len(gone.fetchall())
    return total


class DoorStore:
    def __init__(self, server: Server) -> None:
        self.server = server
        self.base = server.settings.public_base_url
        with server.store.transaction("") as tx:
            for statement in (*TABLES, *WHATSAPP_TABLES):
                tx.execute(statement)

    # --- writes -------------------------------------------------------------------------
    def open(
        self,
        coalition: str,
        owner: str,
        roles: list[Document],
        visibility: str,
        goal: str,
        place: str | None,
        closes_at: datetime,
    ) -> None:
        with self.server.store.transaction(coalition) as tx:
            code = new_code()
            while tx.execute("SELECT 1 FROM server_doors WHERE code = ?", (code,)).fetchone():
                code = new_code()
            tx.execute(
                "INSERT INTO server_doors VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)",
                (
                    coalition,
                    code,
                    secrets.token_urlsafe(9),
                    visibility,
                    goal,
                    place,
                    closes_at.astimezone(UTC).isoformat(),
                    json.dumps(roles),
                ),
            )
        self.arrive(coalition, owner, roles[0]["id"])

    def arrive(self, coalition: str, participant: str, role: str) -> None:
        with self.server.store.transaction(coalition) as tx:
            if not tx.execute(
                "SELECT 1 FROM server_doors WHERE coalition = ?", (coalition,)
            ).fetchone():
                return
            last = tx.execute(
                "SELECT COALESCE(MAX(n), 0) FROM server_door_arrivals WHERE coalition = ?",
                (coalition,),
            ).fetchone()[0]
            tx.execute(
                "INSERT INTO server_door_arrivals VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT (coalition, participant) DO NOTHING",
                (coalition, participant, role, datetime.now(UTC).isoformat(), last + 1),
            )

    def stop(self, coalition: str) -> None:
        with self.server.store.transaction(coalition) as tx:
            tx.execute("UPDATE server_doors SET stopped = 1 WHERE coalition = ?", (coalition,))

    # --- reads --------------------------------------------------------------------------
    def door_row(self, column: str, value: str) -> Document | None:
        with self.server.store.transaction("") as tx:
            row = tx.execute(
                f"SELECT coalition, code, room, visibility, goal, place, closes_at, stopped, "
                f"roles FROM server_doors WHERE {column} = ?",
                (value,),
            ).fetchone()
        if not row:
            return None
        found: Document = {
            "coalition": row[0],
            "code": row[1],
            "room": row[2],
            "visibility": row[3],
            "goal": row[4],
            "place": row[5],
            "closes_at": row[6],
            "stopped": row[7],
            "roles": json.loads(row[8]),
        }
        return found

    def present(self, door: Document) -> list[tuple[str, str, str]]:
        """Arrivals newest first, only for people still in the room."""
        coalition = door["coalition"]
        with self.server.store.transaction(coalition) as tx:
            rows = tx.execute(
                "SELECT participant, role, at FROM server_door_arrivals WHERE coalition = ? "
                "ORDER BY n DESC",
                (coalition,),
            ).fetchall()
        members = self.server.hosts[coalition].state.members
        return [(p, r, a) for p, r, a in rows if p in members]

    def seated(self, door: Document) -> list[Document]:
        coalition = door["coalition"]
        return [
            {"participant": p, "role": r, "at": a, "home": self.home(coalition, p)}
            for p, r, a in self.present(door)
        ]

    def home(self, coalition: str, participant: str) -> str:
        """What the host proves: a WhatsApp binding, else a hosted credential, else a signed
        card at an A2A endpoint. The host cannot tell MCP from A2A, so it never says "mcp"."""
        with self.server.store.transaction("") as tx:
            bound = tx.execute(
                "SELECT 1 FROM whatsapp_bindings WHERE viewer = ?",
                (viewer_key(coalition, participant),),
            ).fetchone()
            hosted = tx.execute(
                "SELECT hosted FROM server_credentials WHERE coalition = ? AND participant = ?",
                (coalition, participant),
            ).fetchone()
        if bound:
            return "whatsapp"
        return "hosted" if hosted and hosted[0] else "a2a"

    def seats(self, door: Document) -> tuple[int, int, dict[str, int]]:
        arrivals = self.present(door)
        used: dict[str, int] = {}
        for _, role, _ in arrivals:
            used[role] = used.get(role, 0) + 1
        return sum(r["count"] for r in door["roles"]), len(arrivals), used

    def is_open(self, door: Document) -> bool:
        stage = self.server.hosts[door["coalition"]].state.stage
        return (
            not door["stopped"]
            and stage != "Dissolve"
            and datetime.fromisoformat(door["closes_at"]) > datetime.now(UTC)
        )

    def open_roles(self, door: Document) -> list[Document]:
        _, _, used = self.seats(door)
        return [
            {"id": r["id"], "label": r["label"], "open": max(0, r["count"] - used.get(r["id"], 0))}
            for r in door["roles"]
        ]

    def choose_role(self, door: Document, requested: str | None) -> str | None:
        free = [r["id"] for r in self.open_roles(door) if r["open"]]
        if requested in free:
            return requested
        return free[0] if free else None

    def view(self, coalition: str) -> Document | None:
        door = self.door_row("coalition", coalition)
        if door is None:
            return None
        seats, filled, _ = self.seats(door)
        labels = {r["id"]: r["label"] for r in door["roles"]}
        with self.server.store.transaction(coalition) as tx:
            knocks = tx.execute(
                "SELECT id, at FROM server_door_knocks WHERE coalition = ? AND state = 'waiting' "
                "AND at > ? ORDER BY at DESC",
                (coalition, knocks_since()),
            ).fetchall()
        return {
            "code": door["code"],
            "link": self.base + "/join#" + door["code"],
            "stopped": bool(door["stopped"]),
            "visibility": door["visibility"],
            "goal": door["goal"],
            "place": door["place"],
            "closes_at": door["closes_at"],
            "seats": seats,
            "filled": filled,
            "arrivals": [
                {**a, "label": labels.get(a["role"], a["role"])} for a in self.seated(door)
            ],
            "knocks": [{"id": k, "at": a} for k, a in knocks],
        }

    def listed(self, box: Box) -> list[Document]:
        with self.server.store.transaction("") as tx:
            rooms = [
                r[0]
                for r in tx.execute(
                    "SELECT room FROM server_doors WHERE visibility = 'nearby' AND stopped = 0"
                ).fetchall()
            ]
        out: list[Document] = []
        for room in rooms:
            door = self.door_row("room", room)
            if door is None or not self.is_open(door):
                continue
            seats, filled, _ = self.seats(door)
            if filled >= seats:
                continue
            lat, lon = position(room, box)
            out.append(
                {
                    "id": room,
                    "goal": door["goal"],
                    "place": door["place"],
                    "seats": seats,
                    "filled": filled,
                    "closes": door["closes_at"],
                    "lat": lat,
                    "lon": lon,
                    "status": "forming",
                    "sample": False,
                }
            )
        return out

    def listed_door(self, room: str) -> Document | None:
        door = self.door_row("room", room)
        if door is None or door["visibility"] != "nearby" or not self.is_open(door):
            return None
        seats, filled, _ = self.seats(door)
        return door if filled < seats else None


class JoinCode(BaseModel):
    code: str = Field(max_length=32)
    display_name: str | None = Field(default=None, min_length=1, max_length=64)
    role: str | None = Field(default=None, max_length=64)
    # An agent from outside brings its own signed card and holds its own keys; it then joins over
    # A2A itself. Without a card the host holds the seat's keys and joins for the person.
    card_url: str | None = Field(default=None, max_length=2048)
    card: Document | None = None


class Answer(BaseModel):
    answer: Literal["yes", "no"]


def mount_door(
    app: FastAPI,
    server: Server,
    store: DoorStore,
    gate: Callable[[Request], None],
    owner: Callable[[Request], str],
    mutation: asyncio.Lock,
    enroll: Callable[..., Any],
) -> None:
    registry = server.registry
    joins, per_code = Limiter(JOIN_PER_CALLER), Limiter(JOIN_PER_CODE)
    knocks, polls = Limiter(KNOCK_PER_CALLER), Limiter(KNOCK_POLL_PER_CALLER)

    def mine(request: Request) -> tuple[str, Document]:
        coalition = owner(request)
        door = store.door_row("coalition", coalition)
        if door is None:
            raise HTTPException(404, "no door")
        return coalition, door

    def reply(coalition: str) -> Document:
        view = store.view(coalition)
        if view is None:
            raise HTTPException(404, "no door")
        return view

    def by_code(request: Request, raw: str) -> Document:
        code = clean_code(raw)
        if not joins.allow(caller(request)) or not per_code.allow(code or raw[:32]):
            raise HTTPException(429, "too many tries")
        door = store.door_row("code", code) if code else None
        if door is None or not store.is_open(door):
            raise HTTPException(404, "door not found")
        return door

    @app.get("/v1/coalition/door", dependencies=[Depends(gate)])
    async def show(request: Request) -> Document:
        return reply(mine(request)[0])

    @app.post("/v1/coalition/door/stop", dependencies=[Depends(gate)])
    async def stop(request: Request) -> Document:
        coalition, _ = mine(request)
        store.stop(coalition)
        return reply(coalition)

    @app.post("/v1/coalition/door/knocks/{knock}", dependencies=[Depends(gate)])
    async def answer(request: Request, knock: str, body: Answer) -> Document:
        coalition, door = mine(request)
        async with mutation:
            if body.answer == "yes" and store.choose_role(door, None) is None:
                raise HTTPException(409, "room is full")
            with server.store.transaction(coalition) as tx:
                row = tx.execute(
                    "SELECT 1 FROM server_door_knocks WHERE id = ? AND coalition = ? "
                    "AND state = 'waiting' AND at > ?",
                    (knock, coalition, knocks_since()),
                ).fetchone()
                if not row:
                    raise HTTPException(404, "knock not found")
            invitation = ""
            if body.answer == "yes":
                invitation = registry.issue_invitation(coalition, "member")["link"].split("#")[1]
            with server.store.transaction(coalition) as tx:
                tx.execute(
                    "UPDATE server_door_knocks SET state = ?, invitation = ? WHERE id = ?",
                    (body.answer, invitation, knock),
                )
        return reply(coalition)

    @app.get("/v1/door/{code}", dependencies=[Depends(gate)])
    async def lookup(request: Request, code: str) -> Document:
        door = by_code(request, code)
        seats, filled, _used = store.seats(door)
        return {
            "goal": door["goal"],
            "place": door["place"],
            "closes_at": door["closes_at"],
            "seats": seats,
            "filled": filled,
            "roles": store.open_roles(door),
        }

    @app.post("/v1/door/join", dependencies=[Depends(gate)])
    async def join(request: Request, body: JoinCode) -> Document:
        door = by_code(request, body.code)
        coalition = door["coalition"]
        async with mutation:
            role = store.choose_role(door, body.role)
            if role is None:
                raise HTTPException(409, "room is full")
            invitation = registry.issue_invitation(coalition, "member")
            try:
                redeemed = registry.redeem(
                    invitation["link"].split("#")[1], server.ports, body.card_url, body.card
                )
                if body.card is None:
                    await enroll(server, redeemed, role)
            except CardError as exc:
                registry.revoke_invitation(coalition, invitation["id"])
                raise HTTPException(400, "card refused: " + exc.reason) from None
            except ValueError, KeyError:
                registry.revoke_invitation(coalition, invitation["id"])
                raise HTTPException(400, "join refused") from None
            registry.set_name(coalition, redeemed["participant"], body.display_name)
            store.arrive(coalition, redeemed["participant"], role)
            return {
                **{k: redeemed[k] for k in ("coalition_id", "participant", "token")},
                "role": role,
                "host_key": public_key_to_jwk(server.key.public_key(), "host"),
            }

    @app.post("/v1/rooms/{room}/knock", dependencies=[Depends(gate)])
    async def knock(request: Request, room: str) -> Document:
        if not knocks.allow(caller(request)):
            raise HTTPException(429, "too many tries")
        door = store.listed_door(room)
        if door is None:
            raise HTTPException(404, "room not found")
        coalition, identifier, token = door["coalition"], new_ulid(), secrets.token_urlsafe(24)
        async with mutation:
            with server.store.transaction(coalition) as tx:
                waiting = tx.execute(
                    "SELECT COUNT(*) FROM server_door_knocks WHERE coalition = ? "
                    "AND state = 'waiting' AND at > ?",
                    (coalition, knocks_since()),
                ).fetchone()[0]
                if waiting >= KNOCKS_OPEN_MAX:
                    raise HTTPException(429, "too many knocks")
                tx.execute(
                    "INSERT INTO server_door_knocks VALUES (?, ?, ?, 'waiting', '', ?)",
                    (identifier, coalition, digest(token), datetime.now(UTC).isoformat()),
                )
        return {"knock": identifier, "secret": token}

    @app.get("/v1/rooms/{room}/knocks/{knock}", dependencies=[Depends(gate)])
    async def poll(request: Request, room: str, knock: str, secret: str = "") -> Document:
        if not polls.allow(caller(request)):
            raise HTTPException(429, "too many tries")
        door = store.door_row("room", room)
        if door is None:
            raise HTTPException(403, "knock refused")
        async with mutation:
            with server.store.transaction(door["coalition"]) as tx:
                row = tx.execute(
                    "SELECT secret, state, invitation, at FROM server_door_knocks "
                    "WHERE id = ? AND coalition = ?",
                    (knock, door["coalition"]),
                ).fetchone()
                expected = row[0] if row else digest("")
                if not hmac.compare_digest(expected, digest(secret)) or not row:
                    raise HTTPException(403, "knock refused")
                if row[1] == "yes" and row[2]:
                    tx.execute(
                        "UPDATE server_door_knocks SET invitation = '' WHERE id = ?", (knock,)
                    )
                    return {"state": "yes", "invitation": row[2]}
        # Nobody answered in time: to the person knocking, that is a no.
        return {"state": "no" if row[1] == "waiting" and row[3] <= knocks_since() else row[1]}


__all__ = ["DoorStore", "Limiter", "caller", "erase_door", "mount_door"]
