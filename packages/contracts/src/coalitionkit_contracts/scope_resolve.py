# SPDX-License-Identifier: Apache-2.0
"""The narrowest scope of several sources, as a pure function (spec: Visibility scopes)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .scope import Scope


@dataclass(frozen=True)
class ScopeSource:
    """One source event of a derived output: its scope and the owner of its sender.

    ``projected`` says the output is built from the source's redacted projection only (its
    ``redact`` paths are already removed from the data the host read), not from the original.
    """

    scope: Scope
    owner: str
    projected: bool = False


@dataclass(frozen=True)
class Membership:
    """Who the members are and who holds each role, at derivation time."""

    members: frozenset[str]
    role_holders: Mapping[str, frozenset[str]]


def principals(source: ScopeSource, membership: Membership) -> frozenset[str]:
    """The resolved principal set of one source: the members who may see it."""
    scope, members = source.scope, membership.members
    match scope.audience:
        case "coalition":
            return members
        case "roles":
            held: set[str] = set()
            for role in scope.roles or []:
                held |= membership.role_holders.get(role, frozenset())
            return frozenset(held) & members
        case "participants":
            return frozenset(scope.participants or []) & members
        case "self":
            return frozenset({source.owner}) & members
        case "host":
            return frozenset()


def resolve_narrowest(sources: Sequence[ScopeSource], membership: Membership) -> Scope:
    """The scope a derived output takes: the intersection of its sources' principal sets.

    Roles resolve to the members holding them now, ``self`` to the source sender's owner. An
    empty intersection becomes ``host``. A source with a non-empty ``redact`` list that is not
    ``projected`` makes the output ``host`` (no redaction path survives a renamed field), and a
    ``projected`` source contributes no redaction paths. When every source is ``coalition`` the
    result is ``coalition``; when every source lists the same roles it stays ``roles``; otherwise
    it is ``participants`` with the sorted intersection.
    """
    if not sources:
        raise ValueError("a derived output needs at least one source")
    if any(s.scope.redact and not s.projected for s in sources):
        return Scope(audience="host")
    common = principals(sources[0], membership)
    for source in sources[1:]:
        common &= principals(source, membership)
    audiences = {s.scope.audience for s in sources}
    if not common:
        return Scope(audience="host")
    if audiences == {"coalition"}:
        return Scope(audience="coalition")
    if audiences == {"roles"} and len({frozenset(s.scope.roles or []) for s in sources}) == 1:
        return Scope(audience="roles", roles=sorted(sources[0].scope.roles or []))
    return Scope(audience="participants", participants=sorted(common))
