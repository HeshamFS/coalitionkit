# SPDX-License-Identifier: Apache-2.0
"""Run independent probes and preserve failures in a signed report."""

import httpx
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coalitionkit_edges.a2a.identity import CardKey, card_keys, fetch_card, verify_card

from .feed_probes import charter, observer
from .operator import Operator
from .probes import chain, host_probes, run_probe
from .report import Document, results, signed_report
from .scenarios import (
    Scenario,
    authorization_rows,
    charter_revision,
    decisions,
    derivation,
    stages,
    steward_gate,
)
from .wire import Participant, enroll

REASONS = {
    "C-02": "Join can be submitted, but charter retrieval is not defined on the A2A send endpoint",
    "C-03": "Requires target-generated member decisions with pinned owner consent keys",
    "C-04": "Requires an inbound endpoint observing the target member's outgoing messages",
    "C-06": "Requires an operator-provisioned vault query fixture",
    "C-07": "Requires two vault endpoints and the PSI vector fixture",
    "C-08": "Requires operator planting of private canaries",
    "C-10": "Requires operator-created tasks in different lifecycle stages",
    "C-12": "Requires an operator-controlled Steward block policy",
    "C-15": "Requires operator-created decision subjects and deadline control",
    "C-16": "scope.json needs controlled sources and membership unavailable over this wire",
    "C-17": "Requires a surface renderer adapter",
    "C-18": "Requires a surface consent interaction adapter",
    "C-19": "Requires authenticated surface viewer sessions",
    "C-21": "Requires operator publication of a new charter revision",
}


async def run(
    target: str,
    level: str,
    invites: list[str],
    *,
    redeem_url: str | None = None,
    key: Ed25519PrivateKey | None = None,
    timeout: float = 20,
    operator: Operator | None = None,
) -> Document:
    tests = results(level)
    for test in tests:
        test["reason"] = REASONS.get(test["id"], "Requires invitations and --redeem-url")
    people: list[Participant] = []
    async with httpx.AsyncClient(timeout=timeout) as http:
        try:
            card = await fetch_card(http, target)
            host = verify_card(card, card_keys(card).get)
        except Exception as exc:
            tests[0].update(status="fail", reason=f"Card verification failed: {type(exc).__name__}")
        else:
            tests[0].update(status="pass", evidence=f"Extension card verifies with key {host.kid}")
            tests[0].pop("reason", None)
            if operator:
                try:
                    created = await operator.create(
                        {
                            "goal": "Coordinate shared tasks",
                            "roles": [{"id": "member"}],
                            "rules": [],
                            "deadline": "2099-01-01T00:00:00Z",
                            "deciders": ["p1", "p2"],
                        }
                    )
                    if created["host_card_url"] != target:
                        raise ValueError("operator created a Coalition on another target")
                    invites = [i["invitation"] for i in created["invitations"]]
                    redeem_url = operator.redeem_url
                except Exception as exc:
                    tests[1].update(status="fail", reason=f"Operator setup failed: {exc}")
                    return signed_report(target, level, tests, key or Ed25519PrivateKey.generate())
            if level in {"host", "member"} and invites and redeem_url:
                try:
                    for invite in invites:
                        person = await enroll(http, target, host, invite, redeem_url)
                        people.append(person)
                        if person.coalition != people[0].coalition:
                            raise ValueError("invitations must name one isolated Coalition")
                        joined = await person.client.send(person.join())
                        if joined.accepted is None:
                            raise AssertionError("join not delivered to joining participant")
                    tests[1]["evidence"] = f"{len(people)} owner-proof joins accepted"
                    if operator:
                        await operator_probes(tests, people, host, http, operator, target)
                    else:
                        await host_probes(tests, people, host)
                except Exception as exc:
                    tests[1].update(
                        status="fail", reason=f"Enrollment failed: {type(exc).__name__}"
                    )
                finally:
                    for person in people:
                        await person.client.close()
    return signed_report(target, level, tests, key or Ed25519PrivateKey.generate())


async def operator_probes(
    tests: list[Document],
    people: list[Participant],
    host: CardKey,
    http: httpx.AsyncClient,
    operator: Operator,
    target: str,
) -> None:
    by_id = {t["id"]: t for t in tests}

    async def acknowledge() -> str:
        return "; ".join([await charter(p, http, operator.feed_url) for p in people])

    await run_probe(by_id["C-02"], acknowledge)
    if "C-09" in by_id:
        await run_probe(by_id["C-09"], lambda: chain(people, host))
    # Run concurrency checks before hidden events enter the log.
    remaining = [
        t for t in tests if t["id"] != "C-09" and not (t["id"] == "C-11" and len(people) >= 2)
    ]
    await host_probes(remaining, people, host)
    if "C-11" in by_id and len(people) >= 2:
        await run_probe(
            by_id["C-11"],
            lambda: observer(people, http, operator.feed_url),
        )
    scenario = Scenario(people, operator, http, host, target)
    for test_id, probe in (
        ("C-10", stages),
        ("C-12", steward_gate),
        ("C-15", decisions),
        ("C-16", derivation),
        ("C-20", authorization_rows),
        ("C-21", charter_revision),
    ):
        if test_id in by_id:
            incomplete = {
                "C-21": "Commitment suspension checked; offer counting unavailable in feed",
            }
            await run_probe(
                by_id[test_id], lambda probe=probe: probe(scenario), incomplete.get(test_id)
            )
