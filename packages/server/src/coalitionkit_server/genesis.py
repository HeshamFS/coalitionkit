# SPDX-License-Identifier: Apache-2.0
"""Genesis drafting, hosted enrollment and owner lifecycle endpoints."""

from __future__ import annotations

import asyncio
import ipaddress
import json
import os
import re
from datetime import UTC, datetime, timedelta, timezone
from typing import TYPE_CHECKING, Literal

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from starlette.responses import JSONResponse

from coalitionkit_contracts import (
    SchemaValidationError,
    public_key_to_jwk,
    sign_owner_proof,
    validate_payload,
)
from coalitionkit_mcp.gateway import build_envelope
from coalitionkit_models import ModelGateway
from coalitionkit_runtime import Acknowledgement
from coalitionkit_runtime.lifecycle import State

from .adapter import Document

if TYPE_CHECKING:
    from .app import Server


class Goal(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    goal: str = Field(min_length=1, max_length=500)
    # The writer's offset from UTC, so "tonight" and "by Friday" mean their evening, not UTC's.
    utc_offset_minutes: int | None = Field(default=None, ge=-840, le=840)


class Role(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")
    label: str = Field(min_length=1, max_length=64)
    count: int = Field(ge=1, le=10000, strict=True)


class Draft(Goal):
    roles: list[Role] = Field(min_length=1)
    needs: list[str]
    deadline: datetime | None
    deciders: Literal["all"] = "all"
    pack: None = None

    @field_validator("deadline")
    @classmethod
    def utc_deadline(cls, value: datetime | None) -> datetime | None:
        if value is not None:
            if value.tzinfo is None:
                raise ValueError("deadline must include a timezone")
            return value.astimezone(UTC)
        return value

    @model_validator(mode="after")
    def unique_roles(self) -> Draft:
        if len({r.id for r in self.roles}) != len(self.roles):
            raise ValueError("duplicate roles")
        return self


class Reading(BaseModel):
    span: tuple[int, int]
    kind: Literal["role", "need", "deadline", "count"]


class DraftResponse(BaseModel):
    draft: Draft
    source: Literal["reader", "model"]
    reading: list[Reading]

    @model_validator(mode="after")
    def valid_spans(self) -> DraftResponse:
        for item in self.reading:
            if not 0 <= item.span[0] < item.span[1] <= len(self.draft.goal):
                raise ValueError("reading span outside goal")
        return self


WORDS = dict(
    zip(
        [
            "one",
            "two",
            "three",
            "four",
            "five",
            "six",
            "seven",
            "eight",
            "nine",
            "ten",
            "eleven",
            "twelve",
            "thirteen",
            "fourteen",
            "fifteen",
            "sixteen",
            "seventeen",
            "eighteen",
            "nineteen",
            "twenty",
        ],
        range(1, 21),
        strict=True,
    )
)
NUMBER = r"(?:\d+|" + "|".join(WORDS) + r"|an?|a)"
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DEADLINE = re.compile(
    rf"\b(?:tonight|today|tomorrow|by (?:{'|'.join(WEEKDAYS)}|\d{{4}}-\d{{2}}-\d{{2}})"
    rf"|in ({NUMBER}) (days?|hours?))\b",
    re.I,
)


def number(value: str) -> int:
    return int(value) if value.isdigit() else WORDS.get(value.lower(), 1)


def read_goal(
    goal: str, now: datetime | None = None, utc_offset_minutes: int | None = None
) -> DraftResponse:
    goal = Goal(goal=goal).goal
    local = timezone(timedelta(minutes=utc_offset_minutes or 0))
    now = (now or datetime.now(UTC)).astimezone(local)
    spans: list[Reading] = []
    deadline = None
    match = DEADLINE.search(goal)
    if match:
        phrase = match[0].lower()
        try:
            if phrase.startswith("in "):
                amount = number(match[1])
                deadline = now + (
                    timedelta(days=amount)
                    if match[2].startswith("day")
                    else timedelta(hours=amount)
                )
            elif phrase.startswith("by "):
                day = phrase[3:]
                if day in WEEKDAYS:
                    deadline = now + timedelta(days=(WEEKDAYS.index(day) - now.weekday()) % 7)
                else:
                    deadline = datetime.fromisoformat(day).replace(tzinfo=local)
                deadline = deadline.replace(hour=23, minute=59, second=59, microsecond=0)
            else:
                deadline = (now + timedelta(days=int(phrase == "tomorrow"))).replace(
                    hour=23, minute=59, second=59, microsecond=0
                )
            spans.append(Reading(span=match.span(), kind="deadline"))
            deadline = deadline.astimezone(UTC)
        except ValueError, OverflowError:
            deadline = None
    roles: dict[str, Role] = {}
    # Counts tied to people/roles, never durations or quantities of requested objects.
    role_pattern = re.compile(
        rf"\b({NUMBER})\s+(of us|people|members?|participants?|labs?|couriers?|"
        r"teams?|volunteers?|organizers?|drivers?|reviewers?|groups?|businesses|business)\b",
        re.I,
    )
    for role_match in role_pattern.finditer(goal):
        label = role_match[2].lower()
        label = "member" if label in {"of us", "people", "participants", "participant"} else label
        label = "business" if label == "businesses" else label
        if label.endswith("s") and label != "business":
            label = label[:-1]
        count = min(number(role_match[1]), 10000)
        if count < 1:
            continue
        if label in roles:
            roles[label].count = min(10000, roles[label].count + count)
        else:
            roles[label] = Role(id=label, label=label, count=count)
        spans.extend(
            [
                Reading(span=role_match.span(1), kind="count"),
                Reading(span=role_match.span(2), kind="role"),
            ]
        )
    needs: list[str] = []
    need = re.search(
        r"\b(?:need|needs|want|wants)\s+(?:to\s+)?(.+?)(?=\s+(?:by|in)\b|\s+tonight\b|\s+today\b|\s+tomorrow\b|[.!?]?$)",
        goal,
        re.I,
    )
    if need:
        needs.append(need[1].strip())
        spans.append(Reading(span=need.span(1), kind="need"))
    return DraftResponse(
        draft=Draft(
            goal=goal,
            roles=list(roles.values()) or [Role(id="member", label="member", count=1)],
            needs=needs,
            deadline=deadline,
        ),
        source="reader",
        reading=spans,
    )


async def draft_goal(
    goal: str, gateway: ModelGateway, utc_offset_minutes: int | None = None
) -> DraftResponse:
    fallback = read_goal(goal, utc_offset_minutes=utc_offset_minutes)
    local_now = datetime.now(UTC).astimezone(timezone(timedelta(minutes=utc_offset_minutes or 0)))
    if not os.environ.get("COALITIONKIT_META_API_KEY"):
        return fallback
    try:
        async with asyncio.timeout(5):
            reply = await gateway.complete(
                "gardener",
                [
                    {
                        "role": "system",
                        "content": "Read a coalition goal into the requested JSON schema. "
                        "Preserve the goal exactly. "
                        "Use character offsets into that goal for reading spans. Give deadlines in "
                        "UTC, reading day words in the writer's local time, now "
                        f"{local_now.isoformat()}. "
                        "Default role member, count 1. "
                        "Use deciders all, pack null, source model. Never invent a deadline.",
                    },
                    {"role": "user", "content": fallback.draft.goal},
                ],
                response_schema=DraftResponse,
            )
            result = DraftResponse.model_validate_json(reply.text)
            if result.draft.goal != fallback.draft.goal:
                raise ValueError("model changed goal")
            result.source = "model"
            return result
    except Exception:
        return fallback


async def enroll_member(server: Server, redeemed: Document, role: str = "member") -> None:
    """Join a redeemed hosted member using the same owner proof as the demo."""
    coalition, participant = redeemed["coalition_id"], redeemed["participant"]
    person = server.registry.hosted_for(coalition, participant)
    jwk = public_key_to_jwk(person.owner_key.public_key(), person.owner_kid)
    envelope = build_envelope(
        person,
        coalition,
        "coalition.join",
        {
            "card_url": person.card_url,
            "owner_key": jwk,
            "owner_proof": sign_owner_proof(
                coalition, participant, person.card_url, jwk, person.owner_key
            ),
            "roles_requested": [role],
            "surfaces": ["web"],
            "vault": "hosted",
        },
        scope={"audience": "coalition"},
    )
    reply = await server.accept(envelope, person.card_url)
    if "error" in reply:
        raise ValueError(f"join refused for {participant}: {reply['error']['code']}")


class Start(BaseModel):
    draft: Draft
    owner_name: str | None = Field(default=None, min_length=1, max_length=64)


class Invitations(BaseModel):
    kind: Literal["member", "business"]
    count: int = Field(ge=1, le=50, strict=True)


class Accept(BaseModel):
    invitation: str
    display_name: str | None = Field(default=None, min_length=1, max_length=64)


class Dissolve(BaseModel):
    reason: Literal["completed", "cancelled"]


def mount_genesis(app: FastAPI, server: Server) -> None:
    if server.settings.genesis == "off":
        return
    registry = server.registry
    mutation = asyncio.Lock()

    def gate(request: Request) -> None:
        if (
            request.method != "DELETE"
            and request.headers.get("content-type", "").split(";")[0] != "application/json"
        ):
            raise HTTPException(403, "JSON required")
        if server.settings.genesis == "local":
            try:
                local = (
                    request.client is not None
                    and ipaddress.ip_address(request.client.host).is_loopback
                )
            except ValueError:
                local = False
            if not local or request.headers.get("origin") != server.settings.public_base_url:
                raise HTTPException(403, "local same-origin request required")

    def owner(request: Request, retry: bool = False) -> str:
        authorization = request.headers.get("authorization", "")
        if not authorization.startswith("Bearer "):
            raise HTTPException(401, "bearer token required")
        token = authorization[7:]
        coalition = registry.owner_coalition(token)
        row = registry.lookup(token)
        if not row and not (retry and coalition):
            raise HTTPException(401, "unauthenticated")
        if not coalition:
            raise HTTPException(403, "owner required")
        return coalition

    @app.post("/v1/genesis/draft", dependencies=[Depends(gate)])
    async def draft(request: Request, body: Goal) -> DraftResponse:
        if server.settings.genesis == "admin":
            from .app import admin

            admin(request, server.settings)
        return await draft_goal(body.goal, server.gateway, body.utc_offset_minutes)

    @app.post("/v1/genesis/start", dependencies=[Depends(gate)])
    async def start(request: Request, body: Start) -> Document:
        # Start authentication always requires a single-use code, including admin deployments.
        value = request.headers.get("authorization", "")
        if not value.startswith("Start "):
            raise HTTPException(401, "start code required")
        async with mutation:
            if not registry.consume_start(value[6:]):
                raise HTTPException(401, "invalid start code")
            charter = {
                "goal": body.draft.goal,
                "roles": [{"id": r.id} for r in body.draft.roles],
                "rules": [],
                "deadline": (
                    body.draft.deadline or datetime.now(UTC) + timedelta(days=7)
                ).isoformat(),
                "deciders": [f"p{i}" for i in range(1, sum(r.count for r in body.draft.roles) + 1)],
            }
            try:
                validate_payload(
                    "coalition.charter",
                    {**charter, "revision": 1, "created_at": datetime.now(UTC).isoformat()},
                )
                created = server.create(charter)
                redeemed = registry.redeem(
                    created["invitations"][0]["invitation"], server.ports, None, None
                )
                await enroll_member(server, redeemed, body.draft.roles[0].id)
            except (ValueError, SchemaValidationError) as exc:
                raise HTTPException(422, str(exc)) from None
            registry.record_owner(
                created["coalition_id"], redeemed["participant"], redeemed["token"]
            )
            return {
                "coalition_id": created["coalition_id"],
                "owner": {"participant": redeemed["participant"], "token": redeemed["token"]},
            }

    @app.post("/v1/invitations", dependencies=[Depends(gate)])
    async def issue(request: Request, body: Invitations) -> Document:
        async with mutation:
            coalition = owner(request)
            return {
                "invitations": [
                    registry.issue_invitation(coalition, body.kind) for _ in range(body.count)
                ]
            }

    @app.delete("/v1/invitations/{identifier}", dependencies=[Depends(gate)], status_code=204)
    async def revoke(request: Request, identifier: str) -> Response:
        registry.revoke_invitation(owner(request), identifier)
        return Response(status_code=204)

    @app.post("/v1/invitations/accept", dependencies=[Depends(gate)])
    async def accept(body: Accept) -> Document:
        async with mutation:
            try:
                redeemed = registry.redeem(body.invitation, server.ports, None, None)
                roles = server.hosts[redeemed["coalition_id"]].state.charter["roles"]
                await enroll_member(server, redeemed, roles[0]["id"])
            except ValueError, KeyError:
                raise HTTPException(400, "invitation refused") from None
            return {k: redeemed[k] for k in ("coalition_id", "participant", "token")}

    @app.post("/v1/coalition/dissolve", dependencies=[Depends(gate)], response_model=None)
    async def dissolve(request: Request, body: Dissolve) -> Document | JSONResponse:
        async with mutation:
            coalition = owner(request, retry=True)
            return dissolve_coalition(server, coalition, body.reason)


def dissolve_coalition(server: Server, coalition: str, reason: str) -> Document | JSONResponse:
    registry, host = server.registry, server.hosts[coalition]
    done: Document = {}
    step = "event"
    try:
        with registry.lock:
            with server.store.transaction(coalition) as tx:
                row = tx.execute(
                    "SELECT progress FROM server_dissolutions WHERE coalition = ?", (coalition,)
                ).fetchone()
            done = json.loads(row[0]) if row else {}
            if "seq" not in done:
                events = server.store.read(coalition)
                event = next((e for e in events if e["type"] == "coalition.dissolve"), None)
                if event is None:
                    result = host.host_emit(
                        "dissolve",
                        {"reason": reason, "skills_written": []},
                        {"audience": "coalition"},
                    )
                    if not isinstance(result, Acknowledgement):
                        raise ValueError("dissolve refused")
                    event = next(
                        e for e in server.store.read(coalition) if e["type"] == "coalition.dissolve"
                    )
                # Reconstruct pre-dissolution state even if the event committed but its
                # progress checkpoint failed (or the process stopped between those writes).
                before = State(coalition)
                for previous in server.store.read(coalition):
                    if previous["seq"] >= event["seq"]:
                        break
                    before.apply(previous)
                tasks = sum(t["status"] not in {"done", "withdrawn"} for t in before.tasks.values())
                done.update(seq=event["seq"], tasks_closed=tasks)
                with server.store.transaction(coalition) as tx:
                    tx.execute(
                        "INSERT INTO server_dissolutions VALUES (?, ?) "
                        "ON CONFLICT (coalition) DO UPDATE SET progress = excluded.progress",
                        (coalition, json.dumps(done)),
                    )
            # Each deletion and its progress marker commit together. Retried cleanup cannot
            # lose counts or require private hosted keys that have already been erased.
            for step in ("vaults_erased", "tokens_revoked", "invitations_revoked"):
                if step in done:
                    continue
                with server.store.transaction(coalition) as tx:
                    if step == "vaults_erased":
                        rows = tx.execute(
                            "UPDATE server_credentials SET hosted = '' "
                            "WHERE coalition = ? AND hosted != '' RETURNING participant",
                            (coalition,),
                        ).fetchall()
                    elif step == "tokens_revoked":
                        rows = tx.execute(
                            "DELETE FROM server_credentials WHERE coalition = ? RETURNING digest",
                            (coalition,),
                        ).fetchall()
                    else:
                        rows = tx.execute(
                            "DELETE FROM server_invites WHERE coalition = ? RETURNING digest",
                            (coalition,),
                        ).fetchall()
                    progress = {**done, step: len(rows)}
                    tx.execute(
                        "UPDATE server_dissolutions SET progress = ? WHERE coalition = ?",
                        (json.dumps(progress), coalition),
                    )
                done = progress
        return done
    except Exception:
        return JSONResponse({"failed": step, "done": done}, status_code=500)
