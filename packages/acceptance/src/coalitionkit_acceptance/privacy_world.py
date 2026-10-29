# SPDX-License-Identifier: Apache-2.0
"""One privacy run: a Coalition with 20 canaries planted in vaults, redactions, private scopes,
plan assignments and PSI inputs. Everything the host sends out is recorded in a ledger."""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coalitionkit_contracts import new_ulid
from coalitionkit_contracts.payloads import Cost, MatchPayload, QueryPayload
from coalitionkit_runtime import Acknowledgement, SQLiteStore
from coalitionkit_vault.psi import Context, Requester, Responder
from coalitionkit_vault.store import Capacity, Facts, Interval, Vault

from .arena import Arena, Document, Participant, Reply, accepted, refusal_code
from .canaries import HOST, STEWARD, Canary, CanaryFactory, Placement, Registry, Shape
from .scanner import Ledger

NAMES = ("p1", "p2", "p3", "p4")
DECIDERS = ["p2", "p3"]
PRIVATE_COST = Cost(minutes=30, money=100, effort="low")


def assigned(first: str, first_to: str, second: str, second_to: str) -> list[Document]:
    return [
        {"task_id": first, "assignee": first_to},
        {"task_id": second, "assignee": second_to},
    ]


def only(*names: str) -> Document:
    return {"audience": "participants", "participants": list(names)}


@dataclass
class PsiOutcome:
    """What the host's relay did with the PSI rounds, and what the requester learned."""

    refusals: list[str] = field(default_factory=lambda: list[str]())
    overlap: list[str] = field(default_factory=lambda: list[str]())
    blobs: int = 0


@dataclass
class PrivacyWorld:
    seed: int
    rng: random.Random = field(init=False)
    registry: Registry = field(default_factory=Registry)
    ledger: Ledger = field(default_factory=Ledger)
    store: SQLiteStore = field(default_factory=SQLiteStore)
    arena: Arena = field(init=False)
    factory: CanaryFactory = field(init=False)
    vaults: dict[str, Vault] = field(default_factory=lambda: dict[str, Vault]())
    tasks: list[str] = field(default_factory=lambda: list[str]())
    event_ids: dict[str, str] = field(default_factory=lambda: dict[str, str]())
    plan_ids: list[str] = field(default_factory=lambda: list[str]())
    psi: PsiOutcome = field(default_factory=PsiOutcome)
    refusals: dict[str, str] = field(default_factory=lambda: dict[str, str]())
    shadows: list[str] = field(default_factory=lambda: list[str]())
    psi_sets: dict[str, list[str]] = field(default_factory=lambda: dict[str, list[str]]())

    def __post_init__(self) -> None:
        self.rng = random.Random(self.seed)
        self.factory = CanaryFactory(self.rng, self.registry)
        self.arena = Arena.open(self.store, DECIDERS)

    # -- plumbing ----------------------------------------------------------------------------

    @property
    def host(self) -> Any:
        return self.arena.host

    @property
    def people(self) -> dict[str, Participant]:
        return self.arena.members

    def record(self, surface: str, viewer: str, label: str, value: object, owner: str = "") -> None:
        self.ledger.record(surface, viewer, label, value, agent_owner=owner)

    def post(self, person: Participant, envelope: Document, label: str) -> Reply:
        """Submit an envelope as ``person`` and record what came back to them."""
        reply = person.submit(envelope)
        if isinstance(reply, Acknowledgement):
            self.record("ack", person.name, label, reply.accepted)
            self.record("receipt", person.name, label, reply.receipt)
        else:
            self.record("error", person.name, label, reply)
        return reply

    def host_emit(self, kind: str, body: Document, scope: Document | None, **kw: Any) -> Reply:
        reply: Reply = self.host.host_emit(kind, body, scope, **kw)
        if not isinstance(reply, Acknowledgement):
            self.record("error", HOST, f"host_emit {kind}", reply)
        return reply

    def plant(
        self, shape: Shape, placement: Placement, owner: str, legit: frozenset[str] = frozenset()
    ) -> Canary:
        return self.factory.make(shape, placement, owner, legit)

    # -- the build ---------------------------------------------------------------------------

    def build(self, on_phase: Callable[[str], None] = lambda _: None) -> None:
        """Run the whole scenario; ``on_phase`` is told after each phase (feeds take deltas)."""
        for name in NAMES:
            self.arena.enroll(name)
            self.vaults[name] = Vault(name)
        self.tasks = [self.arena.need() for _ in range(3)]
        on_phase("enrolled")
        self.plant_vaults()
        self.plant_events()
        on_phase("events planted")
        self.ask_vaults()
        on_phase("queries answered")
        self.run_psi()
        on_phase("psi relayed")
        self.propose_and_decide()
        on_phase("plan proposed")
        self.derive()
        on_phase("derived outputs")

    def plant_vaults(self) -> None:
        facts: dict[str, dict[str, Any]] = {n: {"slots": [], "caps": [], "sets": {}} for n in NAMES}
        numbers_and_slots: list[tuple[str, Shape]] = [
            ("p1", "number"), ("p2", "number"), ("p1", "slot"), ("p4", "slot")
        ]  # fmt: skip
        for owner, shape in numbers_and_slots:
            canary = self.plant(shape, "vault_fact", owner)
            if shape == "number":
                facts[owner]["caps"].append(Capacity(int(canary.planted), "u"))
            else:
                facts[owner]["slots"].append(Interval(canary.planted, canary.extra))
        facts["p2"]["sets"]["k"] = frozenset({self.plant("word", "vault_fact", "p2").planted})
        for owner in ("p1", "p2", "p3"):
            self.vaults[owner].add_private_note(self.plant("document", "vault_note", owner).planted)
        overlap = self.plant("word", "psi_input", "p3").planted
        mine = [overlap, self.plant("word", "psi_input", "p3").planted]
        mine.append(self.plant("word", "psi_input", "p3").planted)
        theirs = [overlap, self.plant("word", "psi_input", "p4").planted]
        self.psi_sets = {"p3": mine, "p4": theirs}
        facts["p3"]["sets"]["psi"] = frozenset(mine)
        facts["p4"]["sets"]["psi"] = frozenset(theirs)
        for name, parts in facts.items():
            self.vaults[name].put(
                f"s-{name}",
                Facts(tuple(parts["slots"]), tuple(parts["caps"]), parts["sets"], PRIVATE_COST),
            )

    def plant_events(self) -> None:
        shapes: list[Shape] = ["number", "word", "slot", "document"]
        for owner in ("p1", "p2", "p4"):
            canary = self.plant(
                self.rng.choice(shapes), "redact", owner, frozenset({HOST, STEWARD})
            )
            scope: Document = {"audience": "coalition", "redact": ["payload.content"]}
            reply = self.post(
                self.people[owner],
                self.people[owner].envelope(
                    "observe", {"source": "chat", "content": canary.planted}, scope
                ),
                "observe redacted",
            )
            self.event_ids[f"redact:{owner}"] = self.source_id(accepted(reply).accepted)
        private: list[tuple[str, Document, list[str]]] = [
            ("p1", {"audience": "self"}, ["p1"]),
            ("p2", only("p2", "p3"), ["p2", "p3"]),
            ("p3", {"audience": "self"}, ["p3"]),
        ]
        for owner, scope, viewers in private:
            legit = frozenset({HOST, STEWARD, *viewers})
            canary = self.plant(self.rng.choice(shapes), "private_scope", owner, legit)
            reply = self.post(
                self.people[owner],
                self.people[owner].envelope(
                    "observe", {"source": "chat", "content": canary.planted}, scope
                ),
                "observe private",
            )
            self.event_ids[f"private:{owner}"] = accepted(reply).accepted["event_id"]

    def ask_vaults(self) -> None:
        kinds = ("feasible", "cost", "availability", "feasible")
        for index, name in enumerate(NAMES):
            body: Document = {
                "query_id": f"q-{name}-0",
                "kind": kinds[index],
                "subject": f"s-{name}",
            }
            accepted(self.host_emit("query", body, only(name)))
            answer = self.vaults[name].answer(QueryPayload.model_validate(body))
            self.record("answer", name, f"vault answer {name}", answer.to_wire())
            self.post(
                self.people[name],
                self.people[name].envelope("answer", answer.to_wire(), only(name)),
                "answer",
            )

    def run_psi(self) -> None:
        task = self.tasks[2]
        query: Document = {
            "query_id": "q-psi",
            "kind": "feasible",
            "subject": "s-p4",
            "task_id": task,
        }
        accepted(self.host_emit("query", query, only("p4")))
        requester_key, responder_key = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
        context = Context(self.host.coalition_id, "m-psi", "p3", "p4", "overlap", task)
        asker = Requester(context, self.psi_sets["p3"], requester_key, responder_key.public_key())
        answerer = Responder(
            context, self.psi_sets["p4"], responder_key, requester_key.public_key()
        )
        setup = answerer.setup()
        self.relay("p4", setup)
        request = asker.request(setup)
        self.relay("p3", request)
        response = answerer.respond(request)
        self.relay("p4", response)
        learned = asker.finish(response)
        self.psi.overlap = learned if isinstance(learned, list) else []

    def relay(self, sender: str, message: MatchPayload) -> None:
        self.psi.blobs += 1
        self.record("psi_blob", HOST, f"{message.round} blob", message.to_wire())
        person = self.people[sender]
        envelope = person.envelope("match", message.to_wire(), only("p3", "p4"))
        code = refusal_code(self.post(person, envelope, f"match {message.round}"))
        if code is not None:
            self.psi.refusals.append(f"{message.round}:{code}")

    def propose_and_decide(self) -> None:
        shadows = [self.plant("word", "assignment", "-", frozenset({HOST, STEWARD}))]
        shadows.append(self.plant("word", "assignment", "-", frozenset({HOST, STEWARD})))
        self.shadows = [s.planted for s in shadows]
        t1, t2 = self.tasks[0], self.tasks[1]
        plans: list[Document] = [
            {
                "assignments": assigned(t1, "p2", t2, self.shadows[0]),
                "objective_scores": {"cost": 1},
            },
            {
                "assignments": assigned(t1, self.shadows[1], t2, "p3"),
                "objective_scores": {"cost": 2},
            },
        ]
        body: Document = {
            "proposal_set_id": new_ulid(),
            "decision_deadline": "2026-10-29T12:00:00Z",
            "plans": plans,
        }
        reply = accepted(self.host_emit("propose", body, {"audience": "coalition"}))
        self.plan_ids = [p["plan_id"] for p in reply.accepted["payload"]["plans"]]
        self.event_ids["propose"] = reply.accepted["event_id"]
        accepted(self.people["p2"].decide("plan", self.plan_ids[0]))

    def derive(self) -> None:
        """Derived outputs: scoped to the narrowest source, and never widened on request."""
        t1 = self.tasks[0]
        for label, source in (("redact:p1", "redact:p1"), ("private:p2", "private:p2")):
            canary_text = self.text_of_event(self.event_ids[source])
            body: Document = {
                "task_ids": [t1],
                "options": [
                    {"option_id": "o1", "summary": "keep the plan"},
                    {"option_id": "o2", "summary": "replan"},
                ],
                "tradeoffs": [canary_text],
                "deciders": ["p2"],
                "decision_deadline": "2026-10-29T12:00:00Z",
            }
            kept = self.host_emit("tension", dict(body), None, sources=[self.event_ids[source]])
            if isinstance(kept, Acknowledgement):
                self.record("derived", HOST, f"tension from {label}", kept.accepted)
            wide = self.host_emit("tension", dict(body), {"audience": "coalition"},
                                  sources=[self.event_ids[source]])  # fmt: skip
            self.refusals[f"widen derived {label}"] = refusal_code(wide) or "accepted"

    @staticmethod
    def source_id(delivered: Document) -> str:
        """The logged event an acknowledgement stands for (a projection names its source)."""
        if delivered["type"] == "coalition.projection":
            return str(delivered["payload"]["source"]["event_id"])
        return str(delivered["event_id"])

    def text_of_event(self, event_id: str) -> str:
        for event in self.arena.events():
            if event["event_id"] == event_id:
                return str(event["payload"].get("content", ""))
        return ""
