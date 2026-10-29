# SPDX-License-Identifier: Apache-2.0
"""Asking the person: the resolvers behind ``decide``, ``approve_commitment`` and
``accept_charter``, and the only place the hosted OWNER key is used.

Under MCP 2026-07-28 a tool that needs the person returns an ``input_required`` result; the host
shows the question, the person answers, and the call comes back with the answer. The SDK runs the
resolvers again on every round and keeps an answer only while the question it was given for
renders the same, so a changed subject or revision asks again instead of reusing the answer.
Only that answer reaches ``sign_decision``; no tool argument can stand in for it.
"""

from __future__ import annotations

from typing import Annotated, Any

from mcp.server.elicitation import AcceptedElicitation, ElicitationResult
from mcp.server.mcpserver.context import Context
from mcp.server.mcpserver.resolve import Elicit, Resolve
from pydantic import BaseModel, Field

from coalitionkit_contracts import sign_consent
from coalitionkit_contracts.payloads import Subject

from .access import authorize, deps_of
from .errors import CoalitionToolError
from .ports import HostedParticipant


class ConsentAnswer(BaseModel):
    """The one thing the person is asked: consent, yes or no."""

    consent: bool = Field(
        title="Consent",
        description="Yes to consent to exactly what is described above, No to refuse.",
    )


def question_text(coalition_id: str, subject: dict[str, Any], choice: str) -> str:
    return (
        f"Coalition {coalition_id}: record your decision on {subject['kind']} {subject['id']} "
        f"at revision {subject['revision']}, choice {choice}. "
        "Only your answer here is signed in your name."
    )


async def _revision_of(ctx: Context, coalition_id: str, kind: str, subject_id: str) -> int:
    hosted = await authorize(ctx, coalition_id)
    revision = await deps_of(ctx).view.subject_revision(
        hosted.participant, coalition_id, kind, subject_id
    )
    if revision is None:
        raise CoalitionToolError("not_authorized", f"no {kind} {subject_id} visible to you")
    return revision


async def charter_revision(ctx: Context, coalition_id: str) -> int:
    """The charter's current revision, read when the question is built and signed for."""
    return await _revision_of(ctx, coalition_id, "charter", coalition_id)


async def commitment_revision(ctx: Context, coalition_id: str, commitment_id: str) -> int:
    return await _revision_of(ctx, coalition_id, "commitment", commitment_id)


async def accept_question(
    coalition_id: str, revision: Annotated[int, Resolve(charter_revision)]
) -> Elicit[ConsentAnswer]:
    subject = {"kind": "charter", "id": coalition_id, "revision": revision}
    return Elicit(question_text(coalition_id, subject, coalition_id), ConsentAnswer)


async def approve_question(
    coalition_id: str,
    commitment_id: str,
    revision: Annotated[int, Resolve(commitment_revision)],
) -> Elicit[ConsentAnswer]:
    subject = {"kind": "commitment", "id": commitment_id, "revision": revision}
    return Elicit(question_text(coalition_id, subject, commitment_id), ConsentAnswer)


async def decide_question(
    ctx: Context, coalition_id: str, subject: Subject, choice: str
) -> Elicit[ConsentAnswer]:
    await authorize(ctx, coalition_id)
    if subject.kind != "tension_option" and choice != subject.id:
        raise CoalitionToolError("schema_invalid", "choice must equal the subject id")
    return Elicit(question_text(coalition_id, subject.to_wire(), choice), ConsentAnswer)


Answer = Annotated[ElicitationResult[ConsentAnswer], Resolve(decide_question)]
AcceptAnswer = Annotated[ElicitationResult[ConsentAnswer], Resolve(accept_question)]
ApproveAnswer = Annotated[ElicitationResult[ConsentAnswer], Resolve(approve_question)]


def given(answer: ElicitationResult[ConsentAnswer]) -> bool | None:
    """The person's yes or no, or None when they declined or cancelled."""
    return answer.data.consent if isinstance(answer, AcceptedElicitation) else None


def sign_decision(
    hosted: HostedParticipant,
    coalition_id: str,
    subject: dict[str, Any],
    choice: str,
    consent: bool,
    now: str,
) -> dict[str, Any]:
    """A ``coalition.decide`` payload whose ``consent_sig`` is by the participant's OWNER key.

    ``consent`` must be the value the person gave in the elicitation: callers pass nothing else.
    """
    payload: dict[str, Any] = {
        "subject": subject,
        "choice": choice,
        "consent": consent,
        "decided_at": now,
    }
    payload["consent_sig"] = sign_consent(
        coalition_id, payload, hosted.owner_key, hosted.owner_kid, participant=hosted.participant
    )
    return payload


__all__ = [
    "AcceptAnswer",
    "Answer",
    "ApproveAnswer",
    "ConsentAnswer",
    "given",
    "sign_decision",
]
