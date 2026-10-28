# SPDX-License-Identifier: Apache-2.0
"""Typed answers and private-note non-disclosure."""

import pytest
from coalitionkit_vault.answer import DeadlineExceeded
from coalitionkit_vault.canary import Canaries
from coalitionkit_vault.store import Capacity, Facts, Interval, Vault

from coalitionkit_contracts.payloads import Cost, QueryPayload
from coalitionkit_contracts.validate import validate_payload


@pytest.mark.parametrize("kind", ["feasible", "availability", "cost"])
def test_answers(kind: str) -> None:
    vault = Vault("alice")
    canaries = Canaries.plant(vault, 20)
    cost = Cost(minutes=30, money=125, effort="low")
    vault.put(
        "meeting",
        Facts(
            slots=(Interval("2026-10-28T10:00:00Z", "2026-10-28T11:00:00Z"),),
            cost=cost,
        ),
    )
    query = QueryPayload.model_validate(
        {
            "query_id": "q",
            "kind": kind,
            "subject": "meeting",
            "deadline_ms": 100,
        }
    )
    result = vault.answer(query).to_wire()
    validate_payload("coalition.answer", result)
    assert result == {"query_id": "q", "result": cost.to_wire() if kind == "cost" else "yes"}
    assert not canaries.scan(result)
    assert vault.answer(query) == vault.answer(query)
    assert vault.answer(query.model_copy(update={"subject": "unknown"})).result == "no"
    with pytest.raises(DeadlineExceeded):
        vault.answer(query, elapsed_ms=100)


def test_records_and_canaries() -> None:
    vault = Vault("alice")
    canaries = Canaries.plant(vault, 20)
    vault.put("zero", Facts(capacities=(Capacity(0, "units"),)))
    vault.put("stock", Facts(capacities=(Capacity(2, "units"),)))
    vault.put("set", Facts(sets={"skills": frozenset({"private-skill"})}))
    for subject in ("zero", "stock", "set", *canaries.values):
        query = QueryPayload(query_id="q", kind="feasible", subject=subject, deadline_ms=10)
        result = vault.answer(query)
        assert result.result == ("yes" if subject in ("stock", "set") else "no")
        assert not canaries.scan(result.to_wire())
        assert vault.answer(query.model_copy(update={"kind": "cost"})).result == "no"
        assert vault.answer(query.model_copy(update={"kind": "availability"})).result == "no"
    assert canaries.scan({"nested": [canaries.values[0]]}) == (canaries.values[0],)
    assert canaries.scan(canaries.values[0].encode()) == (canaries.values[0],)
    escaped = '"' + "".join(f"\\u{ord(c):04x}" for c in canaries.values[0]) + '"'
    assert canaries.scan(escaped) == (canaries.values[0],)
    with pytest.raises(ValueError):
        Capacity(-1, "units")
    with pytest.raises(ValueError):
        Interval("2026-10-28T11:00:00Z", "2026-10-28T10:00:00Z")
    with pytest.raises(ValueError):
        Interval("2026-10-28T10:00:00", "2026-10-28T11:00:00")
