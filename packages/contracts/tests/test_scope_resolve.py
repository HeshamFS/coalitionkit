# SPDX-License-Identifier: Apache-2.0
"""resolve_narrowest against spec/vectors/scope.json."""

from __future__ import annotations

from typing import Any

import pytest
from examples import load_vector

from coalitionkit_contracts import Membership, Scope, ScopeSource, principals, resolve_narrowest

VECTOR = load_vector("scope.json")


def membership(case: dict[str, Any]) -> Membership:
    return Membership(
        members=frozenset(case["members"]),
        role_holders={role: frozenset(ids) for role, ids in case["role_holders"].items()},
    )


def sources(case: dict[str, Any]) -> list[ScopeSource]:
    return [
        ScopeSource(Scope.model_validate(s["scope"]), s["owner"], s.get("projected", False))
        for s in case["sources"]
    ]


@pytest.mark.parametrize("case", VECTOR["cases"], ids=[c["name"] for c in VECTOR["cases"]])
def test_vector_case(case: dict[str, Any]) -> None:
    result = resolve_narrowest(sources(case), membership(case))
    assert result.to_wire() == case["expected"]


def test_no_sources_is_an_error() -> None:
    with pytest.raises(ValueError, match="at least one source"):
        resolve_narrowest([], Membership(frozenset(), {}))


def test_the_result_is_never_wider_than_any_source() -> None:
    for case in VECTOR["cases"]:
        mem, srcs = membership(case), sources(case)
        result = ScopeSource(resolve_narrowest(srcs, mem), "nobody")
        allowed = principals(result, mem)
        for source in srcs:
            assert allowed <= principals(source, mem), case["name"]


def test_order_of_sources_does_not_matter() -> None:
    for case in VECTOR["cases"]:
        mem, srcs = membership(case), sources(case)
        assert resolve_narrowest(srcs, mem) == resolve_narrowest(srcs[::-1], mem), case["name"]


def test_a_derived_output_never_carries_redaction_paths() -> None:
    for case in VECTOR["cases"]:
        result = resolve_narrowest(sources(case), membership(case))
        assert result.redact is None, case["name"]
