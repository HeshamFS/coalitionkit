# SPDX-License-Identifier: Apache-2.0
"""Allowlisted answers; private notes never enter this computation."""

from coalitionkit_contracts.payloads import AnswerPayload, Cost, QueryPayload

from .store import Facts


class DeadlineExceeded(ValueError):
    """The response budget has expired; do not emit an answer."""


def answer(facts: Facts | None, query: QueryPayload, *, elapsed_ms: int = 0) -> AnswerPayload:
    if type(elapsed_ms) is not int or elapsed_ms < 0:
        raise ValueError("invalid elapsed time")
    if elapsed_ms >= query.deadline_ms:
        raise DeadlineExceeded("query deadline exceeded")
    feasible = facts is not None and (
        bool(facts.slots)
        or any(capacity.amount > 0 for capacity in facts.capacities)
        or any(facts.sets.values())
    )
    result: str | Cost = "no"
    if query.kind == "availability":
        result = "yes" if facts is not None and facts.slots else "no"
    elif query.kind == "feasible":
        result = "yes" if feasible else "no"
    elif feasible and facts is not None and facts.cost is not None:
        result = facts.cost
    return AnswerPayload.model_validate({"query_id": query.query_id, "result": result})
