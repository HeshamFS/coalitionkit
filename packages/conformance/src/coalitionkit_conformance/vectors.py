# SPDX-License-Identifier: Apache-2.0
"""Local normative scope vectors; these alone never certify a remote host."""

import json

from coalitionkit_contracts import Membership, Scope, ScopeSource, resolve_narrowest
from coalitionkit_contracts.resources import spec_path

from .operator import OperatorUnavailable


async def scope_vectors() -> str:
    path = spec_path("vectors", "scope.json")
    if not path.is_file():
        raise OperatorUnavailable("Local spec/vectors/scope.json is unavailable")
    cases = json.loads(path.read_text(encoding="utf-8"))["cases"]
    for case in cases:
        membership = Membership(
            frozenset(case["members"]),
            {role: frozenset(ids) for role, ids in case["role_holders"].items()},
        )
        sources = [
            ScopeSource(Scope.model_validate(s["scope"]), s["owner"], s.get("projected", False))
            for s in case["sources"]
        ]
        actual = resolve_narrowest(sources, membership).to_wire()
        if actual != case["expected"]:
            raise AssertionError(f"scope vector {case['name']}: {actual} != {case['expected']}")
    return f"{len(cases)} local scope vectors match"
