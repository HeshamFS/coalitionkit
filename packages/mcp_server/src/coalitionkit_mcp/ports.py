# SPDX-License-Identifier: Apache-2.0
"""The seams the MCP server plugs into: who a bearer token is, and what a participant may see.

``HostPort`` (where signed envelopes go) is the edge's own port and is reused as is.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


@dataclass(frozen=True)
class HostedParticipant:
    """One participant and the two hosted keys that act for it. Never shared between participants.

    ``agent_key`` signs envelopes; ``owner_key`` signs consent and only after the person answered.
    """

    participant: str
    card_url: str
    agent_key: Ed25519PrivateKey = field(repr=False)
    agent_kid: str
    owner_key: Ed25519PrivateKey = field(repr=False)
    owner_kid: str


class TokenPort(Protocol):
    """Maps a bearer access token to exactly one participant."""

    async def participant_for(self, token: str) -> HostedParticipant | None:
        """The participant the token belongs to, or None when the token is not valid."""
        ...


class ViewPort(Protocol):
    """What one participant may read. Every method is scoped to the participant it is given.

    Implementations return only what that participant's scopes allow (originals where nothing is
    redacted, projections elsewhere, stubs outside the scope for log reads); the server filters
    the shape again with allowlists but never widens it.
    """

    async def is_member(self, participant: str, coalition_id: str) -> bool: ...

    async def coalitions(self, participant: str) -> list[dict[str, Any]]:
        """Summaries of the Coalitions the participant belongs to."""
        ...

    async def coalition(self, participant: str, coalition_id: str) -> dict[str, Any] | None:
        """One summary (``coalition_id``, ``goal``, ``roles``, ``status``), or None."""
        ...

    async def charter(self, participant: str, coalition_id: str) -> dict[str, Any] | None:
        """The current charter payload, including its ``revision``."""
        ...

    async def my_tasks(self, participant: str, coalition_id: str) -> list[dict[str, Any]]: ...

    async def log(self, participant: str, coalition_id: str, since: int) -> list[dict[str, Any]]:
        """Entries with ``seq`` above ``since``, each an original, a projection or a stub."""
        ...

    async def pending_questions(self, participant: str, coalition_id: str) -> list[dict[str, Any]]:
        """Open ``coalition.query`` items addressed to the participant's vault."""
        ...

    async def surface(self, participant: str, coalition_id: str, device: str) -> dict[str, Any]:
        """The data of the participant's live surface for the MCP App view."""
        ...

    async def subject_revision(
        self, participant: str, coalition_id: str, kind: str, subject_id: str
    ) -> int | None:
        """The current revision of a subject the participant may see, or None."""
        ...


class SkillsPort(Protocol):
    async def skills(self, participant: str, coalition_id: str) -> list[dict[str, Any]]: ...
