# SPDX-License-Identifier: Apache-2.0
"""Web search for the room's agents: public words out, real URLs back, every step visible.

A query is built by code from public room facts only (the goal and the need), never from a vault.
Before it leaves the host it is screened: the Steward's deterministic core policies run on it as
if it were a message to the whole room, a street address refuses it, and so does any private
value a seat holds (its free-text answers and the notes it kept private). A refused query is
written down as a stop and nothing is sent. The provider's own queries (the Meta tool may
rephrase) are screened again when the answer comes back; hits from a query that fails are
dropped. Each search leaves an activity line on the Table and is reported through
``on_activity`` with the tool ``search:web``.
"""

from __future__ import annotations

import asyncio
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import replace
from typing import TYPE_CHECKING, Any, cast

from coalitionkit_contracts import Scope, new_ulid
from coalitionkit_models import MissingKeyError, SearchHit, SearchProvider, make_search
from coalitionkit_models.search import web_url
from coalitionkit_steward import StewardContext, Subject, core_policies
from coalitionkit_steward.conditions import evaluate_all

from ..adapter import Document
from . import budget, public
from .needs import tidy
from .seats import read_state

if TYPE_CHECKING:
    from .engine import RoomEngine

Activity = Callable[[Document], Awaitable[None]]
SEARCH_TIMEOUT_S = 120.0
QUERY_MAX = 200
KEEP = 20  # searches kept in ``room.search``
NOTES = "_room_notes"
_LOCKS: dict[tuple[str, str], asyncio.Lock] = {}
BRIEF = "_room_brief"
#: A street address: "12 Mill Road", "Mill Road 12", "Hauptstraße 5". It never leaves the host.
STREET = re.compile(
    r"\b\d{1,5}[a-z]?\s+(?:[A-Za-zÀ-ÿ'.-]+\s+){0,3}"
    r"(?:street|st|road|rd|avenue|ave|lane|ln|drive|dr|way|boulevard|blvd|place|pl|square)\b"
    r"|\b[A-Za-zÀ-ÿ-]*(?:stra(?:ß|ss)e|str\.|weg|gasse|allee|platz|ring|damm)\s+\d{1,5}[a-z]?\b",
    re.I,
)
#: Need kinds whose words ask for a fact from outside the room.
FINDABLE = re.compile(
    r"\b(find|look up|search|where|which|recommend|nearby|near|shop|store|venue|place|"
    r"rent|hire|buy|book|tickets?|opening hours|options?)\b",
    re.I,
)


def provider(engine: RoomEngine) -> SearchProvider | None:
    """The host's search provider, made once from the model settings; None when search is off."""
    server: Any = engine.server
    if not hasattr(server, "_web_search"):
        gateway = server.gateway
        server._web_search = make_search(gateway.settings, meter=gateway.meter)
    return cast(SearchProvider | None, server._web_search)


def query_for(facts: Document, where: str | None = None) -> str:
    """The words a search sends: the need and the goal, nothing any one person said privately.

    ``where`` is a seat's published answer to a pack's public search question (its city); the
    query is then the need and that answer only, so the pages are about the place itself.
    """
    words = f"{facts['need']['title']}: {facts['goal']}"
    if where:
        words = f"{facts['need']['title']} in {where}"  # the goal would pull pages about it
    return tidy(" ".join(words.split()), QUERY_MAX)


def private_values(engine: RoomEngine, coalition: str, seats: list[str]) -> list[str]:
    """Every private text any seat holds: free-text answers and notes kept private."""
    found: list[str] = []
    for who in seats:
        vault = engine.vault(coalition, who)
        for note in cast(list[Document], vault.get(NOTES, [])):
            found.append(str(note.get("text", "")))
        record = cast(Document, vault.get(BRIEF, {}))
        for q in cast(list[Document], record.get("questions", [])):
            if q.get("status") == "answered" and q.get("kind") == "text" and not q.get("public"):
                found.append(str(q.get("answer", "")))
    return [v.strip() for v in found if len(v.strip()) >= 4]


def screen(query: str, private: list[str], coalition: str, who: str) -> str | None:
    """Why this query may not leave the host, or None when it may."""
    if not query.strip():
        return "the query is empty"
    if STREET.search(query):
        return "it holds a street address"
    low = query.lower()
    if any(v.lower() in low for v in private):
        return "it holds something a person said privately"
    subject = Subject(
        "message",
        coalition,
        new_ulid(),
        1,
        "coalition.observe",
        who,
        Scope(audience="coalition"),
        {"source": "web", "content": query},
    )
    matched = evaluate_all(core_policies(), subject, StewardContext())
    stopped = [m.policy.id for m in matched if m.policy.then != "allow"]
    return f"the Steward's policy {stopped[0]} matched" if stopped else None


def hook(engine: RoomEngine, coalition: str) -> Activity | None:
    """The room's tool-activity recorder, bound to this room; None for a room that is not traced."""
    from .activity import records, reporter

    return reporter(engine, coalition) if records(engine, coalition) else None


async def report(on_activity: Activity | None, activity: Document) -> None:
    if on_activity is None:
        return
    try:
        await on_activity(activity)
    except Exception:  # a recorder that fails must not stop the search
        return


def done(base: Document, result: str, status: str, ms: int, **over: str) -> Document:
    """One activity in the shared shape: seat, agent, tool, args, result, status, ms, refs."""
    return {**base, **over, "result": result, "status": status, "ms": ms, "refs": []}


def remember(engine: RoomEngine, coalition: str, entry: Document) -> None:
    def add(doc: Document) -> None:
        doc["search"] = [*doc.get("search", []), entry][-KEEP:]

    engine.update(coalition, add)


async def search(
    engine: RoomEngine,
    coalition: str,
    who: str,
    query: str,
    *,
    agent: str = "hosted",
    need: str | None = None,
    seats: list[str] | None = None,
    limit: int | None = None,
    on_activity: Activity | None = None,
) -> list[SearchHit] | None:
    """Screened hits for ``query``, [] when refused or failed, None when search is off."""
    found = provider(engine)
    if found is None:
        return None
    settings = engine.server.gateway.settings
    most = min(limit or settings.search_max_results, settings.search_max_results)
    on_activity = on_activity or hook(engine, coalition)
    members = seats if seats is not None else sorted((await read_state(engine, coalition)).members)
    private = private_values(engine, coalition, members)
    base: Document = {"seat": who, "agent": agent, "tool": "search:web", "args": query}
    refused = screen(query, private, coalition, who)
    if not refused and budget.reached(engine, coalition):
        refused = "the room has used its model budget"
    if refused:
        engine.start_activity(
            coalition, "searching", f"Search refused: {refused}", seat=who, need=need,
            source="search", state="failed",
        )  # fmt: skip
        remember(engine, coalition, {**_entry(who, need, "", found.name), "refused": refused})
        await report(on_activity, done(base, refused, "failed", 0, args="(refused)"))
        return []
    entry = engine.start_activity(
        coalition, "searching", f"Searching the web: {query}", seat=who, need=need, source="search"
    )
    await report(on_activity, done(base, "", "started", 0))
    started = time.monotonic()
    try:
        async with asyncio.timeout(SEARCH_TIMEOUT_S):
            run = await found.search(query, limit=most, coalition_id=coalition, participant=who)
    except Exception as exc:
        ms = round((time.monotonic() - started) * 1000)
        why = "no key" if isinstance(exc, MissingKeyError) else type(exc).__name__
        engine.end_activity(coalition, entry, state="failed", ms=ms, error=why)
        remember(engine, coalition, {**_entry(who, need, query, found.name), "failed": why})
        await report(on_activity, done(base, why, "failed", ms))
        return []
    ms = round((time.monotonic() - started) * 1000)
    ran = [q for q in run.queries if q.strip()] or [query]
    bad = [q for q in ran if screen(q, private, coalition, who)]
    hits = [] if bad else list(run.hits)
    first = hits[0].title if hits else "nothing found"
    line = f"{len(hits)} found; first: {first}" if hits else first
    engine.end_activity(
        coalition, entry, state="failed" if bad else "done", ms=ms, cost=run.cost_micro_usd,
        tokens=list(run.tokens), label=f"Searched the web: {query} ({line})",
    )  # fmt: skip
    remember(
        engine,
        coalition,
        {
            **_entry(who, need, query, found.name),
            "ran": ran,
            "count": len(hits),
            "first": first if hits else "",
            "ms": ms,
            "cost": run.cost_micro_usd,
            **({"refused": "the provider rephrased it into words the host refuses"} if bad else {}),
        },
    )
    await report(on_activity, done(base, tidy(line, 160), "failed" if bad else "done", ms))
    return hits


def _entry(who: str, need: str | None, query: str, name: str) -> Document:
    return {"id": new_ulid(), "seat": who, "need": need, "query": query, "provider": name}


def links(hits: list[SearchHit]) -> list[Document]:
    """Hits as the plain records a result carries under ``data.web``."""
    return [
        {"title": h.title, "url": h.url, "snippet": h.snippet, "source": h.source} for h in hits
    ]


def shown_links(data: object) -> list[Document]:
    """The web sources a result's data carries, each a real http(s) URL; anything else dropped.

    An agent from outside can send any data, so this is checked before a screen shows it.
    """
    if not isinstance(data, dict):
        return []
    raw: Any = cast(Document, data).get("web")
    out: list[Document] = []
    for item in cast(list[Any], raw if isinstance(raw, list) else []):
        if not isinstance(item, dict):
            continue
        row = cast(Document, item)
        url = web_url(row.get("url"))
        if url:
            out.append({"title": tidy(str(row.get("title") or url), 140), "url": url})
    return out[:10]


def cached(engine: RoomEngine, coalition: str, need: str) -> list[SearchHit] | None:
    """Hits an earlier search for this need already found (offers search, makers reuse)."""
    found = engine.read(coalition).get("search_hits", {}).get(need)
    if not isinstance(found, list):
        return None
    return [SearchHit(**cast(Document, h)) for h in cast(list[Any], found)]


def keep(engine: RoomEngine, coalition: str, need: str, hits: list[SearchHit]) -> None:
    def put(doc: Document) -> None:
        doc["search_hits"] = {**doc.get("search_hits", {}), need: links(hits)}

    engine.update(coalition, put)


async def for_place(
    engine: RoomEngine, coalition: str, who: str, facts: Document, where: str
) -> None:
    """One search for this need in one seat's own place, once per place, hits merged."""
    need = str(facts["need"]["id"])
    key = where.casefold()
    lock = _LOCKS.setdefault((coalition, f"{need}@{key}"), asyncio.Lock())
    async with lock:
        if key in engine.read(coalition).get("search_places", {}).get(need, []):
            return
        hits = await search(engine, coalition, who, query_for(facts, where), need=need)
        if not hits:
            return
        tagged = [replace(h, title=f"{h.title} ({where})") for h in hits]

        def put(doc: Document) -> None:
            done = doc.setdefault("search_places", {}).setdefault(need, [])
            done.append(key)
            old = list(doc.get("search_hits", {}).get(need, []))
            seen = {h["url"] for h in old}
            new = [h for h in links(tagged) if h["url"] not in seen]
            doc["search_hits"] = {**doc.get("search_hits", {}), need: old + new}

        engine.update(coalition, put)
        names = "; ".join(h.title for h in hits[:3])
        engine.feed_add(coalition, who, f"Your agent looked up {where} on the web: {names}.")


async def for_need(
    engine: RoomEngine, coalition: str, who: str, facts: Document, *, mine_only: bool = False
) -> list[SearchHit] | None:
    """Hits for a need, searched once per need and reused; None when search is off."""
    if provider(engine) is None:
        return None
    need = str(facts["need"]["id"])
    places = public.search_places(engine, coalition) if facts["need"]["kind"] == "place" else {}
    if places:  # each seat searches its own published answer; the hits are kept together
        for seat in [who] if mine_only else sorted(places):
            if seat in places:
                await for_place(engine, coalition, seat, facts, places[seat])
        return cached(engine, coalition, need)
    lock = _LOCKS.setdefault((coalition, need), asyncio.Lock())
    async with lock:  # seats offer at once: the first searches, the others reuse it
        hits = cached(engine, coalition, need)
        if hits:
            return hits
        hits = await search(engine, coalition, who, query_for(facts), need=need)
        if hits:
            keep(engine, coalition, need, hits)
        return hits


def searched_by(engine: RoomEngine, coalition: str, need: str) -> str | None:
    """The seat whose search found this need's pages."""
    done = [s for s in engine.read(coalition).get("search", []) if s.get("need") == need]
    return str(done[-1]["seat"]) if done else None


def wants_fact(facts: Document) -> bool:
    """A list or a draft searches only when its need asks for something from outside the room."""
    need = facts["need"]
    return bool(FINDABLE.search(f"{need['title']} {need.get('detail') or ''}"))


async def at_offer(
    engine: RoomEngine,
    coalition: str,
    who: str,
    goal: str,
    needs: list[Document],
    offered: set[str],
) -> None:
    """A hosted agent that offers on a place need looks it up on the web, once per need.

    What it finds goes to its own person's feed now and to the maker later (reused, not paid
    for twice); the result shows the sources.
    """
    if provider(engine) is None:
        return
    for need in needs:
        if need["kind"] != "place" or need["id"] not in offered:
            continue
        if public.search_places(engine, coalition):
            await for_need(engine, coalition, who, {"need": need, "goal": goal}, mine_only=True)
            continue
        if cached(engine, coalition, str(need["id"])) is not None:
            continue
        hits = await for_need(engine, coalition, who, {"need": need, "goal": goal})
        if hits and searched_by(engine, coalition, str(need["id"])) == who:
            names = "; ".join(h.title for h in hits[:3])
            engine.feed_add(
                coalition, who, f"Your agent looked up {need['title']} on the web: {names}."
            )


SEARCH_FIELDS = ("id", "seat", "need", "query", "provider", "ran", "count", "first", "ms")


def search_feed(doc: Document) -> list[Document]:
    """``room.search``: what the agents searched, newest last. Queries hold only public words."""
    out: list[Document] = []
    for entry in cast(list[Document], doc.get("search", [])):
        row = {k: entry.get(k) for k in SEARCH_FIELDS}
        row["ran"] = list(entry.get("ran") or [])
        row["count"] = int(entry.get("count") or 0)
        row["stopped"] = entry.get("refused") or entry.get("failed")
        out.append(row)
    return out


class RoomSearchPort:
    """The MCP server's ``web_search`` for outside agents: the same screen, the same Table line."""

    def __init__(self, server: Any) -> None:
        self._server = server

    async def web_search(self, participant: str, coalition_id: str, query: str) -> Document | None:
        engine: RoomEngine | None = self._server.room
        if engine is None or provider(engine) is None:
            return None
        seats = sorted((await read_state(engine, coalition_id)).members)
        private = private_values(engine, coalition_id, seats)
        refused = screen(query, private, coalition_id, participant)
        hits = await search(engine, coalition_id, participant, query, agent="mcp", seats=seats)
        if refused or hits is None:
            return {"refused": refused or "web search is off"}
        return {"results": [{k: h[k] for k in ("title", "url", "snippet")} for h in links(hits)]}
