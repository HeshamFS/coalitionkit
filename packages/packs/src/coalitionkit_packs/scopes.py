# SPDX-License-Identifier: Apache-2.0
"""A pack may narrow a scope, never widen it."""

from __future__ import annotations

from coalitionkit_contracts import Scope

_RANK = {"host": 0, "self": 1, "participants": 2, "roles": 2, "coalition": 3}
#: Audiences a pack template may name. A pack names no people and sets no coalition-wide default.
PACK_AUDIENCES = frozenset({"host", "self", "roles"})


class ScopeWidenError(ValueError):
    """A pack scope reaches someone the scope it narrows does not."""


def check_not_wider(base: Scope, candidate: Scope) -> None:
    """Raise ScopeWidenError unless ``candidate`` reaches no one ``base`` does not.

    Redaction paths of ``base`` must all stay in ``candidate``. Roles and participants lists
    must be subsets; a roles scope and a participants scope are not comparable, so swapping
    one for the other counts as widening.
    """
    if _RANK[candidate.audience] > _RANK[base.audience]:
        raise ScopeWidenError(f"{candidate.audience} is wider than {base.audience}")
    if candidate.audience == base.audience:
        for attr in ("participants", "roles"):
            extra = set(getattr(candidate, attr) or []) - set(getattr(base, attr) or [])
            if extra:
                raise ScopeWidenError(f"{attr} {sorted(extra)} are not in the base scope")
    elif base.audience in ("participants", "roles") and candidate.audience in (
        "participants",
        "roles",
    ):
        raise ScopeWidenError("roles and participants scopes are not comparable")
    dropped = set(base.redact or []) - set(candidate.redact or [])
    if dropped:
        raise ScopeWidenError(f"redaction paths {sorted(dropped)} were dropped")


def narrow(base: Scope, candidate: Scope) -> Scope:
    """``candidate`` if it is no wider than ``base``; otherwise ScopeWidenError."""
    check_not_wider(base, candidate)
    return candidate
