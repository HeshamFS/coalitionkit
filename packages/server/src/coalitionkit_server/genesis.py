# SPDX-License-Identifier: Apache-2.0
"""Genesis drafting, hosted enrollment and owner lifecycle endpoints."""

from __future__ import annotations

import asyncio
import ipaddress
import json
import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Literal
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse

from coalitionkit_contracts import (
    SchemaValidationError,
    jwk_thumbprint,
    public_key_to_jwk,
    sign_owner_proof,
    validate_payload,
)
from coalitionkit_mcp.gateway import build_envelope
from coalitionkit_packs import Pack
from coalitionkit_runtime import Acknowledgement
from coalitionkit_runtime.lifecycle import State

from .adapter import Document
from .genesis_draft import (
    NUMBER,
    Draft,
    DraftResponse,
    Goal,
    ModelDraft,
    Reading,
    Role,
    draft_goal,
    number,
    read_goal,
)
from .packs import PackRef, public_pack, suggest_pack

__all__ = ["DraftResponse", "ModelDraft", "draft_goal", "read_goal"]

if TYPE_CHECKING:
    from .app import Server


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
            request.method not in {"DELETE", "GET"}
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
            if not local or not same_origin(request):
                raise HTTPException(403, "local same-origin request required")

    def same_origin(request: Request) -> bool:
        # Browsers send no Origin on a same-origin GET; they send Sec-Fetch-Site, which page
        # scripts cannot set. A cross-site GET says "cross-site", so it stays refused.
        origin = request.headers.get("origin")
        if origin is not None:
            return origin == server.settings.public_base_url
        # The Host check keeps a DNS-rebound page (same-origin to the browser) out.
        return (
            request.method == "GET"
            and request.headers.get("sec-fetch-site") == "same-origin"
            and request.headers.get("host") == urlsplit(server.settings.public_base_url).netloc
        )

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

    def chosen_pack(ref: PackRef) -> Pack:
        pack = server.packs.get((ref.name, ref.version))
        if pack is None:
            raise HTTPException(422, "pack is not installed")
        return pack

    mount_drafting(app, server, gate, chosen_pack)
    mount_start(app, server, gate, chosen_pack, mutation)

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
            return {
                **{k: redeemed[k] for k in ("coalition_id", "participant", "token")},
                "host_key": public_key_to_jwk(server.key.public_key(), "host"),
            }

    @app.post("/v1/coalition/dissolve", dependencies=[Depends(gate)], response_model=None)
    async def dissolve(request: Request, body: Dissolve) -> Document | JSONResponse:
        async with mutation:
            coalition = owner(request, retry=True)
            return dissolve_coalition(server, coalition, body.reason)


def mount_drafting(
    app: FastAPI,
    server: Server,
    gate: Callable[[Request], None],
    chosen_pack: Callable[[PackRef], Pack],
) -> None:
    @app.get("/v1/packs", dependencies=[Depends(gate)])
    async def packs(request: Request) -> list[Document]:
        if server.settings.genesis == "admin":
            from .app import admin

            admin(request, server.settings)
        return [public_pack(pack) for pack in server.packs.values()]

    @app.post("/v1/genesis/draft", dependencies=[Depends(gate)])
    async def draft(request: Request, body: Goal) -> DraftResponse:
        if server.settings.genesis == "admin":
            from .app import admin

            admin(request, server.settings)
        pack = chosen_pack(body.pack) if body.pack else None
        result = await draft_goal(body.goal, server.gateway, body.utc_offset_minutes)
        result.draft.pack = body.pack
        result.suggested = suggest_pack(body.goal, server.packs)
        result.vocabulary = {}
        if pack:
            result.vocabulary = public_pack(pack)["vocabulary"]
            result.reading = [r for r in result.reading if r.kind not in {"role", "count"}]
            roles: list[Role] = []
            for identifier, spec in pack.manifest.roles.items():
                labels = sorted({identifier, spec.label or identifier}, key=len, reverse=True)
                pattern = re.compile(
                    rf"\b({NUMBER})\s+("
                    + "|".join(re.escape(label) + "s?" for label in labels)
                    + r")\b",
                    re.I,
                )
                matches = [m for m in pattern.finditer(body.goal) if number(m[1]) > 0]
                count = min(sum(number(m[1]) for m in matches), 10000) if matches else 1
                roles.append(Role(id=identifier, label=spec.label or identifier, count=count))
                for match in matches:
                    result.reading.extend(
                        [
                            Reading(span=match.span(1), kind="count"),
                            Reading(span=match.span(2), kind="role"),
                        ]
                    )
            result.draft.roles = roles
        return result


def mount_start(
    app: FastAPI,
    server: Server,
    gate: Callable[[Request], None],
    chosen_pack: Callable[[PackRef], Pack],
    mutation: asyncio.Lock,
) -> None:
    registry = server.registry

    @app.post("/v1/genesis/start", dependencies=[Depends(gate)])
    async def start(request: Request, body: Start) -> Document:
        # Start authentication always requires a single-use code, including admin deployments.
        value = request.headers.get("authorization", "")
        if not value.startswith("Start "):
            raise HTTPException(401, "start code required")
        if body.draft.pack:
            pack = chosen_pack(body.draft.pack)
            if any(role.id not in pack.manifest.roles for role in body.draft.roles):
                raise HTTPException(422, "draft role is not a pack role")
        async with mutation:
            if not registry.consume_start(value[6:]):
                raise HTTPException(401, "invalid start code")
            charter: Document = {
                "goal": body.draft.goal,
                "roles": [{"id": r.id} for r in body.draft.roles],
                "rules": [],
                "deadline": (
                    body.draft.deadline or datetime.now(UTC) + timedelta(days=7)
                ).isoformat(),
                "deciders": [f"p{i}" for i in range(1, sum(r.count for r in body.draft.roles) + 1)],
            }
            if body.draft.pack:
                charter["pack"] = body.draft.pack.model_dump()
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
            with server.store.transaction(created["coalition_id"]) as tx:
                tx.execute(
                    "INSERT INTO server_genesis VALUES (?, ?, ?)",
                    (
                        created["coalition_id"],
                        redeemed["participant"],
                        json.dumps(body.draft.needs),
                    ),
                )
            server.gardener.start(created["coalition_id"])
            return {
                "coalition_id": created["coalition_id"],
                "owner": {"participant": redeemed["participant"], "token": redeemed["token"]},
                # The key members pin at join; the browser verifies the log against it.
                "host_key": created["host_key"],
            }


def owner_lessons(server: Server, coalition: str, ids: list[str]) -> Document:
    """Titles of the written lessons the owner may read (a lesson is scoped to its sources)."""
    with server.store.transaction(coalition) as tx:
        owner = tx.execute(
            "SELECT participant FROM server_owners WHERE coalition = ?", (coalition,)
        ).fetchone()
        rows = tx.execute(
            "SELECT name, audience, body FROM pack_lessons WHERE coalition = ?", (coalition,)
        ).fetchall()
    member = server.hosts[coalition].state.members.get(owner[0]) if owner else None
    if member is None:
        return {}
    # A lesson's audience is the owner keys of the members its sources reached.
    key = jwk_thumbprint(member["owner_key"])
    titles: Document = {}
    for name, audience, body in rows:
        if name in ids and key in json.loads(audience):
            titles[name] = {"title": json.loads(body)["title"]}
    return titles


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
                done.update(
                    seq=event["seq"],
                    tasks_closed=tasks,
                    # The owner's closing screen names the lessons; the feed that would carry
                    # the dissolve event closes with the owner's access.
                    skills_written=event["payload"]["skills_written"],
                    lessons=owner_lessons(server, coalition, event["payload"]["skills_written"]),
                )
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
