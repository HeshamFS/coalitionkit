# SPDX-License-Identifier: Apache-2.0
"""Acceptance test 7: chaos. Kill the host, drop the database, race the deciders, drop a viewer.

Each scenario returns a ``Recorder``; the pass conditions are its counters
(``lost_events``, ``duplicate_events``, ``max_decisions_per_revision``).

These run in process against the host. ``chaos_server`` runs the same cases against the real
server process, including a killed process and Postgres in Docker. There is no message bus to
split: the host uses an in-process bus.
"""

from __future__ import annotations

import time
from collections import Counter
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

from coalitionkit_runtime import Acknowledgement, EventStore, PostgresStore, SQLiteStore

from .arena import DEADLINE, PUBLIC, Arena, Document, Participant, accepted, refusal_code
from .faults import FaultyStore, InjectedFault
from .metrics import Recorder
from .watch import Viewer, check_log

DECIDERS = ("alice", "bob")
MEMBERS = ("alice", "bob", "cara")


def open_store(directory: Path, database_url: str | None = None) -> FaultyStore:
    """A file-backed SQLite store (or Postgres when a URL is given) wrapped for fault injection."""
    inner: EventStore = (
        PostgresStore(database_url)
        if database_url
        else SQLiteStore(str(directory / "coalition.sqlite3"))
    )
    return FaultyStore(inner)


def decisions_per_revision(events: list[Document]) -> Counter[tuple[str, str, int, str]]:
    counts: Counter[tuple[str, str, int, str]] = Counter()
    for event in events:
        if event["type"] == "coalition.decide":
            ref = event["payload"]["subject"]
            counts[(ref["kind"], ref["id"], ref["revision"], event["on_behalf_of"])] += 1
    return counts


def audit(recorder: Recorder, arena: Arena, acknowledged: set[str]) -> None:
    """Count what must be zero: acknowledged events missing from the log, and repeats."""
    events = arena.events()
    stored = [event["event_id"] for event in events]
    recorder.count("lost_events", len(acknowledged - set(stored)))
    recorder.count("duplicate_events", len(stored) - len(set(stored)))
    recorder.count("events", check_log(arena.host))
    per_revision = decisions_per_revision(events)
    recorder.count("max_decisions_per_revision", max(per_revision.values(), default=0))


class Tape:
    """Remembers the event IDs the host acknowledged, to compare with the log afterwards."""

    def __init__(self) -> None:
        self.acknowledged: set[str] = set()

    def submit(self, person: Participant, envelope: Document) -> Acknowledgement[Document]:
        reply = accepted(person.submit(envelope))
        self.acknowledged.add(envelope["event_id"])
        return reply


def seed_negotiation(arena: Arena) -> tuple[str, str]:
    """Three members, one task and one plan waiting for the deciders. Returns (task, plan)."""
    for name in MEMBERS:
        arena.enroll(name)
    task = arena.need()
    (plan,) = arena.propose({task: "cara"})
    return task, plan


def kill_and_restart(directory: Path, database_url: str | None = None) -> Recorder:
    """Kill the host twice in the middle of a negotiation and restart it from the store.

    First kill: the commit of alice's decision landed but its reply was lost. Second kill: the
    commit of bob's decision never happened. The scripts retry the same envelopes.
    """
    recorder = Recorder("chaos_kill_restart")
    tape = Tape()
    store = open_store(directory, database_url)
    arena = Arena.open(store, DECIDERS)
    _, plan = seed_negotiation(arena)
    tape.acknowledged.update(event["event_id"] for event in arena.events())
    before = arena.events()

    alice_env = arena.members["alice"].decision_envelope("plan", plan)
    store.arm("after")
    try:
        arena.members["alice"].submit(alice_env)
    except InjectedFault:
        recorder.count("replies_lost")
    arena, store = _restart(arena, directory, database_url, recorder)
    first = tape.submit(arena.members["alice"], alice_env)
    seq: int = first.receipt["payload"]["seq"]
    recorder.count(
        "replayed_receipts_match_log",
        int(arena.events()[seq - 1]["event_id"] == alice_env["event_id"]),
    )

    bob_env = arena.members["bob"].decision_envelope("plan", plan)
    store.arm("inside")
    try:
        arena.members["bob"].submit(bob_env)
    except InjectedFault:
        recorder.count("commits_lost")
    during = arena.events()
    arena, store = _restart(arena, directory, database_url, recorder)
    tape.submit(arena.members["bob"], bob_env)

    after = arena.events()
    recorder.count("prefix_intact", int(after[: len(before)] == before))
    recorder.count("events_added_by_retries", len(after) - len(before))
    recorder.count("not_committed_before_retry", len(during) - len(before) - 1)
    recorder.count(
        "plan_decided", int(arena.host.state.subject("plan", plan)["status"] == "decided")
    )
    audit(recorder, arena, tape.acknowledged)
    arena.close()
    return recorder


def _restart(
    arena: Arena, directory: Path, database_url: str | None, recorder: Recorder
) -> tuple[Arena, FaultyStore]:
    """Drop the host and its connection; build a new host from the stored log and time it."""
    old = arena.host.store
    if isinstance(old, FaultyStore):
        old.close()
    started = time.perf_counter()
    store = open_store(directory, database_url)
    fresh = arena.restarted(store, arena.host.private_key)
    _ = fresh.host.state  # the first read folds the whole log back into state
    recorder.sample("recovery_s", time.perf_counter() - started)
    return fresh, store


def drop_connection(rounds: int = 12) -> Recorder:
    """Drop the database before, during and after commits; retried envelopes land exactly once."""
    recorder = Recorder("chaos_drop_connection")
    store = FaultyStore(SQLiteStore())
    arena = Arena.open(store, DECIDERS)
    tape = Tape()
    for name in MEMBERS:
        arena.enroll(name)
    tasks = [arena.need() for _ in range(rounds)]
    viewer = Viewer(arena.host, "watcher")
    tape.acknowledged.update(event["event_id"] for event in arena.events())
    alice = arena.members["alice"]
    pattern = ("before", "inside", "after")
    for index, task in enumerate(tasks):
        envelope = alice.offer_envelope(task, 30, 5)
        store.arm(pattern[index % 3])
        if index % 4 == 3:
            store.arm("before")  # a second failure on the first retry
        started = time.perf_counter()
        for _ in range(5):
            try:
                tape.submit(alice, envelope)
                break
            except InjectedFault:
                recorder.count("retries")
        else:
            raise AssertionError("the envelope was never accepted")
        recorder.sample("accept_with_retries_s", time.perf_counter() - started)
    viewer.pump()
    recorder.count("faults_fired", len(store.fired))
    audit(recorder, arena, tape.acknowledged)
    recorder.count("viewer_lost_events", viewer.lost(recorder.counter("events")))
    arena.close()
    return recorder


def concurrent_deciders(rounds: int = 20) -> Recorder:
    """Both deciders answer at once, each twice from two connections; one answer per decider."""
    recorder = Recorder("chaos_concurrent_deciders")
    arena = Arena.open(SQLiteStore(), DECIDERS)
    for name in MEMBERS:
        arena.enroll(name)
    tape = Tape()
    tape.acknowledged.update(event["event_id"] for event in arena.events())
    outcomes: Counter[str] = Counter()
    for index in range(rounds):
        task = arena.need()
        tension = _tension(arena, task)
        picks = {"alice": "a", "bob": "a" if index % 2 == 0 else "b"}
        attempts: list[tuple[str, Document]] = []
        for name, pick in picks.items():
            for _ in range(2):
                person = arena.members[name]
                envelope = person.decision_envelope("tension_option", tension, 1, pick)
                attempts.append((name, envelope))
        results = _race(arena, attempts)
        for (name, envelope), reply in zip(attempts, results, strict=True):
            if isinstance(reply, Acknowledgement):
                tape.acknowledged.add(envelope["event_id"])
                outcomes[f"accepted:{name}"] += 1
            else:
                outcomes[f"refused:{refusal_code(reply)}"] += 1
        status = arena.host.state.subject("tension_option", tension)["status"]
        outcomes[f"outcome:{status}"] += 1
    for key, amount in sorted(outcomes.items()):
        recorder.count(key.replace(":", "_"), amount)
    audit(recorder, arena, tape.acknowledged)
    arena.close()
    return recorder


def _tension(arena: Arena, task: str) -> str:
    body: Document = {
        "task_ids": [task],
        "options": [
            {"option_id": "a", "summary": "First"},
            {"option_id": "b", "summary": "Second"},
        ],
        "tradeoffs": [],
        "deciders": list(DECIDERS),
        "decision_deadline": DEADLINE,
    }
    reply = accepted(arena.host.host_emit("tension", body, PUBLIC))
    return reply.accepted["payload"]["tension_id"]


def _race(arena: Arena, attempts: list[tuple[str, Document]]) -> list[object]:
    gate = Barrier(len(attempts))

    def go(item: tuple[str, Document]) -> object:
        name, envelope = item
        gate.wait()
        return arena.members[name].submit(envelope)

    with ThreadPoolExecutor(max_workers=len(attempts)) as pool:
        return list(pool.map(go, attempts))


def viewer_disconnects_with_consent_open() -> Recorder:
    """A decider's viewer goes away with a plan consent open and comes back later."""
    recorder = Recorder("chaos_viewer_disconnect")
    store = SQLiteStore()
    arena = Arena.open(store, DECIDERS)
    _, plan = seed_negotiation(arena)
    tape = Tape()
    tape.acknowledged.update(event["event_id"] for event in arena.events())
    bob = arena.members["bob"]
    viewer = Viewer(arena.host, "bob")
    viewer.pump()
    viewer.disconnect()
    tape.submit(arena.members["alice"], arena.members["alice"].decision_envelope("plan", plan))
    for _ in range(5):
        tape.submit(
            arena.members["cara"], arena.members["cara"].observe_envelope("while bob is away")
        )
    recorder.count("consent_still_open", _open_consents(arena, plan, "bob"))
    recorder.count(
        "plan_still_pending", int(arena.host.state.subject("plan", plan)["status"] == "pending")
    )
    started = time.perf_counter()
    viewer.reconnect()
    caught_up = viewer.pump()
    recorder.sample("catch_up_s", time.perf_counter() - started)
    recorder.count("events_caught_up", caught_up)
    tape.submit(bob, bob.decision_envelope("plan", plan))
    viewer.pump()
    recorder.count(
        "plan_decided", int(arena.host.state.subject("plan", plan)["status"] == "decided")
    )
    audit(recorder, arena, tape.acknowledged)
    recorder.count("viewer_lost_events", viewer.lost(recorder.counter("events")))
    arena.close()
    return recorder


def _open_consents(arena: Arena, plan: str, decider: str) -> int:
    with arena.host.store.transaction(arena.host.coalition_id) as tx:
        rows = tx.execute(
            "SELECT status FROM consents WHERE subject_id = ? AND decider = ?", (plan, decider)
        ).fetchall()
    return sum(1 for row in rows if row[0] == "pending")


SCENARIOS: dict[str, Callable[..., Recorder]] = {
    "kill_and_restart": kill_and_restart,
    "drop_connection": drop_connection,
    "concurrent_deciders": concurrent_deciders,
    "viewer_disconnect": viewer_disconnects_with_consent_open,
}
