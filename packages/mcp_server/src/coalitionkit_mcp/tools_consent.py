# SPDX-License-Identifier: Apache-2.0
"""The three tools that carry owner authority: ``decide``, ``approve_commitment`` and
``accept_charter``.

Each one asks the person (see ``elicit``). The hosted owner key signs ``consent_sig`` with the
person's answer and nothing else; a ``consent`` or any other flag in the arguments is ignored.
"""

from __future__ import annotations

from typing import Annotated, Any

from mcp.server.mcpserver.context import Context
from mcp.server.mcpserver.resolve import Resolve
from mcp_types import CallToolResult

from coalitionkit_contracts.payloads import Subject

from .access import authorize, deps_of, rfc3339
from .elicit import (
    AcceptAnswer,
    Answer,
    ApproveAnswer,
    charter_revision,
    commitment_revision,
    given,
    sign_decision,
)
from .errors import CoalitionToolError
from .gateway import send
from .results import ok
from .tools_write import ack

NO_ANSWER = "the person did not answer the question"


async def _record(
    ctx: Context,
    coalition_id: str,
    subject: dict[str, Any],
    choice: str,
    consented: bool | None,
) -> dict[str, Any]:
    """Sign the person's answer with the owner key and send it. Returns the accepted envelope."""
    hosted = await authorize(ctx, coalition_id)
    if consented is None:
        raise CoalitionToolError("not_authorized", NO_ANSWER)
    deps = deps_of(ctx)
    payload = sign_decision(hosted, coalition_id, subject, choice, consented, rfc3339(deps.clock()))
    return await send(deps.host, hosted, coalition_id, "coalition.decide", payload)


async def decide(
    coalition_id: str,
    subject: Subject,
    choice: str,
    consent: bool = False,
    *,
    ctx: Context,
    answer: Answer,
) -> CallToolResult:
    """Record the person's decision on a subject at a revision.

    The person is asked inside this call. The consent argument is ignored: only their answer
    is signed.
    """
    consented = given(answer)
    wire = subject.to_wire()
    accepted = await _record(ctx, coalition_id, wire, choice, consented)
    data = ack(accepted, subject=wire, choice=choice, consent=consented)
    return ok("decide", data, f"Decision recorded: consent {consented}.")


async def approve_commitment(
    coalition_id: str,
    commitment_id: str,
    *,
    ctx: Context,
    revision: Annotated[int, Resolve(commitment_revision)],
    answer: ApproveAnswer,
) -> CallToolResult:
    """Approve a commitment at its current revision, after the person confirms it."""
    consented = given(answer)
    subject = {"kind": "commitment", "id": commitment_id, "revision": revision}
    accepted = await _record(ctx, coalition_id, subject, commitment_id, consented)
    data = ack(accepted, commitment_id=commitment_id, revision=revision, consent=consented)
    return ok("approve_commitment", data, f"Commitment {commitment_id}: consent {consented}.")


async def accept_charter(
    coalition_id: str,
    *,
    ctx: Context,
    revision: Annotated[int, Resolve(charter_revision)],
    answer: AcceptAnswer,
) -> CallToolResult:
    """Accept the charter at its current revision, after the person confirms it."""
    consented = given(answer)
    subject = {"kind": "charter", "id": coalition_id, "revision": revision}
    accepted = await _record(ctx, coalition_id, subject, coalition_id, consented)
    data = ack(accepted, coalition_id=coalition_id, revision=revision, consent=consented)
    return ok("accept_charter", data, f"Charter revision {revision}: consent {consented}.")
