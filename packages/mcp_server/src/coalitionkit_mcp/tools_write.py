# SPDX-License-Identifier: Apache-2.0
"""The write tools that carry no owner authority. Each becomes one signed envelope.

``join_coalition`` needs only a valid token; every other tool needs membership. The envelope's
sender and ``on_behalf_of`` come from the token's participant, never from an argument.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Literal

from mcp.server.mcpserver.context import Context
from mcp_types import CallToolResult

from coalitionkit_contracts import new_ulid, public_key_to_jwk, sign_owner_proof
from coalitionkit_contracts.payloads import Cost, Evidence, Target

from .access import authenticate, authorize, deps_of, rfc3339
from .errors import CoalitionToolError
from .gateway import send
from .results import ok
from .tools_read import parse_invite

OFFER_VALIDITY = timedelta(hours=24)


def ack(accepted: dict[str, Any], **extra: Any) -> dict[str, Any]:
    """The acknowledgement fields every write result carries, plus tool-specific ones."""
    return {
        "accepted": True,
        "event_id": accepted.get("event_id"),
        "seq": accepted.get("seq"),
        **extra,
    }


async def join_coalition(invite: str, roles: list[str], ctx: Context) -> CallToolResult:
    """Join a Coalition from an invitation link or Coalition ID, with the roles you ask for."""
    hosted = await authenticate(ctx)
    coalition_id = parse_invite(invite)
    deps = deps_of(ctx)
    owner_jwk = public_key_to_jwk(hosted.owner_key.public_key(), hosted.owner_kid)
    payload: dict[str, Any] = {
        "card_url": hosted.card_url,
        "owner_key": owner_jwk,
        "owner_proof": sign_owner_proof(
            coalition_id, hosted.participant, hosted.card_url, owner_jwk, hosted.owner_key
        ),
        "roles_requested": roles,
        "surfaces": ["mcp_app"],
        "vault": "hosted",
    }
    accepted = await send(deps.host, hosted, coalition_id, "coalition.join", payload)
    summary = await deps.view.coalition(hosted.participant, coalition_id) or {}
    charter = await deps.view.charter(hosted.participant, coalition_id)
    data = ack(
        accepted,
        coalition_id=coalition_id,
        granted_roles=summary.get("roles", []),
        charter=charter or {},
    )
    return ok("join_coalition", data, f"Joined Coalition {coalition_id}.")


async def answer_question(
    coalition_id: str, query_id: str, result: Literal["yes", "no"] | Cost, ctx: Context
) -> CallToolResult:
    """Answer an open question from your vault: yes, no or a cost."""
    hosted = await authorize(ctx, coalition_id)
    answer: Any = result if isinstance(result, str) else result.to_wire()
    payload = {"query_id": query_id, "result": answer}
    accepted = await send(deps_of(ctx).host, hosted, coalition_id, "coalition.answer", payload)
    return ok("answer_question", ack(accepted, query_id=query_id), f"Answered {query_id}.")


async def make_offer(
    coalition_id: str,
    target: Target,
    capacity: int,
    cost: Cost,
    ctx: Context,
    valid_until: str | None = None,
) -> CallToolResult:
    """Offer capacity against a need or task. Defaults to an offer valid for 24 hours."""
    hosted = await authorize(ctx, coalition_id)
    deps = deps_of(ctx)
    offer_id = new_ulid()
    payload: dict[str, Any] = {
        "offer_id": offer_id,
        "target": target.to_wire(),
        "capacity": capacity,
        "cost": cost.to_wire(),
        "valid_until": valid_until or rfc3339(deps.clock() + OFFER_VALIDITY),
    }
    accepted = await send(deps.host, hosted, coalition_id, "coalition.offer", payload)
    return ok("make_offer", ack(accepted, offer_id=offer_id), f"Offer {offer_id} made.")


async def commit(
    coalition_id: str,
    task_id: str,
    status: Literal["pending", "withdrawn"],
    ctx: Context,
    commitment_id: str | None = None,
    revision: int | None = None,
) -> CallToolResult:
    """Create a commitment (status pending) or withdraw one (status withdrawn, with its ID).

    Never approves: approval is a separate decision the person confirms.
    """
    hosted = await authorize(ctx, coalition_id)
    if status == "withdrawn" and commitment_id is None:
        raise CoalitionToolError("schema_invalid", "withdrawing needs the commitment_id")
    if status == "pending" and commitment_id is not None:
        raise CoalitionToolError("schema_invalid", "a new commitment gets its ID from the server")
    minted = commitment_id or new_ulid()
    payload: dict[str, Any] = {"commitment_id": minted, "task_id": task_id, "status": status}
    if revision is not None:
        payload["revision"] = revision
    accepted = await send(deps_of(ctx).host, hosted, coalition_id, "coalition.commit", payload)
    return ok(
        "commit",
        ack(accepted, commitment_id=minted, status=status),
        f"Commitment {minted} is {status}.",
    )


async def report_ripple(
    coalition_id: str, change: str, invalidates: list[str], ctx: Context
) -> CallToolResult:
    """Report a change and the task IDs it invalidates."""
    hosted = await authorize(ctx, coalition_id)
    payload = {"change": change, "invalidates": invalidates}
    accepted = await send(deps_of(ctx).host, hosted, coalition_id, "coalition.ripple", payload)
    return ok("report_ripple", ack(accepted), "Ripple reported.")


async def report_done(
    coalition_id: str, task_id: str, evidence: list[Evidence], ctx: Context
) -> CallToolResult:
    """Report an approved task done, with evidence."""
    hosted = await authorize(ctx, coalition_id)
    payload = {"task_id": task_id, "evidence": [item.to_wire() for item in evidence]}
    accepted = await send(deps_of(ctx).host, hosted, coalition_id, "coalition.done", payload)
    return ok("report_done", ack(accepted, task_id=task_id), f"Task {task_id} reported done.")


async def leave_coalition(coalition_id: str, ctx: Context) -> CallToolResult:
    """Leave the Coalition. Your open offers are withdrawn."""
    hosted = await authorize(ctx, coalition_id)
    accepted = await send(deps_of(ctx).host, hosted, coalition_id, "coalition.leave", {})
    return ok("leave_coalition", ack(accepted), f"Left Coalition {coalition_id}.")
