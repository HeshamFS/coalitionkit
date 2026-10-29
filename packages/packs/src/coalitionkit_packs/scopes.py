# SPDX-License-Identifier: Apache-2.0
"""A pack may narrow a scope, never widen it."""

from __future__ import annotations

from coalitionkit_contracts import Membership, Scope, ScopeSource, principals

#: Audiences a pack template may name. A pack names no people and sets no coalition-wide default.
PACK_AUDIENCES = frozenset({"host", "self", "roles"})


class ScopeWidenError(ValueError):
    """A pack scope reaches someone the scope it narrows does not, or that cannot be shown."""


def check_not_wider(
    base: Scope,
    candidate: Scope,
    *,
    owner: str | None = None,
    membership: Membership | None = None,
) -> None:
    """Raise ScopeWidenError unless ``candidate`` provably reaches no one ``base`` does not.

    With ``owner`` (the sender's owner) and ``membership`` the two scopes are resolved to
    recipient sets and compared. Without them only conversions whose subset relation holds for
    every possible membership are accepted: anything to ``host``, ``coalition`` to anything,
    equal audiences with subset lists, and ``self`` to ``self``. Converting ``participants`` or
    ``roles`` to ``self`` (or between roles and participants) needs the resolved sets, so it
    is refused. The candidate must also keep every redaction path of ``base``.
    """
    if membership is not None and owner is not None:
        wider = principals(ScopeSource(candidate, owner), membership) - principals(
            ScopeSource(base, owner), membership
        )
        if wider:
            raise ScopeWidenError(f"candidate reaches {sorted(wider)}, which the base does not")
    elif not _structurally_narrower(base, candidate):
        raise ScopeWidenError(
            f"cannot show that {candidate.audience} is within {base.audience} "
            "without the owner and membership"
        )
    dropped = set(base.redact or []) - set(candidate.redact or [])
    if dropped:
        raise ScopeWidenError(f"redaction paths {sorted(dropped)} were dropped")


def _structurally_narrower(base: Scope, candidate: Scope) -> bool:
    if candidate.audience == "host" or base.audience == "coalition":
        return True
    if candidate.audience != base.audience:
        return False
    if base.audience in ("self", "host"):
        return True
    for attr in ("participants", "roles"):
        if not set(getattr(candidate, attr) or []) <= set(getattr(base, attr) or []):
            return False
    return True


def narrow(
    base: Scope,
    candidate: Scope,
    *,
    owner: str | None = None,
    membership: Membership | None = None,
) -> Scope:
    """``candidate`` if it is provably no wider than ``base``; otherwise ScopeWidenError."""
    check_not_wider(base, candidate, owner=owner, membership=membership)
    return candidate
