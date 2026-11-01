# SPDX-License-Identifier: Apache-2.0
"""Member-owned hosted agent actions exposed to the room."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, HTTPException, Request
from jsonschema.exceptions import ValidationError
from referencing.exceptions import Unresolvable
from starlette.responses import JSONResponse

from coalitionkit_contracts import SchemaValidationError, new_ulid, validate_payload
from coalitionkit_contracts.payloads import Window
from coalitionkit_mcp.gateway import build_envelope
from coalitionkit_surfaces.app import Viewer

from .adapter import Document
from .packs import private_extension, viewer_schema

if TYPE_CHECKING:
    from .app import Server


def hosted_routes(app: FastAPI, server: Server, coalition: str) -> None:
    def hosted(who: str) -> Any:
        try:
            return server.registry.hosted_for(coalition, who)
        except ValueError:
            raise HTTPException(409, "your agent sends offers") from None

    @app.post("/v1/agent/offer")
    async def offer(body: Document, who: Viewer) -> JSONResponse:
        person = hosted(who)
        host = server.hosts[coalition]
        if set(body) - {"need_id", "cost", "window", "ext"}:
            return JSONResponse({"error": "schema_invalid"}, 422)
        need_id = body.get("need_id")
        visible = host.view(who)["events"].values()
        need = next(
            (
                e["payload"]
                for e in visible
                if e["type"] == "coalition.need" and e["payload"].get("need_id") == need_id
            ),
            None,
        )
        if need is None:
            return JSONResponse({"error": "not_authorized"}, 403)
        payload: Document = {
            "offer_id": new_ulid(),
            "target": {"kind": "need", "id": need_id},
            "capacity": 1,
            "cost": body.get("cost", {"minutes": 0, "money": 0, "effort": "low"}),
            "valid_until": need["window"]["end"],
        }
        try:
            if "window" in body:
                window = Window.model_validate(body["window"])
                payload["valid_until"] = window.end
            if "ext" in body:
                payload["ext"] = body["ext"]
            validate_payload("coalition.offer", payload)
        except SchemaValidationError, ValueError:
            return JSONResponse({"error": "schema_invalid"}, 422)
        pack = server.bound_pack(coalition)
        if "ext" in body:
            if pack is None or "offer" not in pack.schemas:
                return JSONResponse({"error": "schema_invalid"}, 422)
            if private_extension(viewer_schema(pack, "offer"), body["ext"]):
                return JSONResponse({"error": "private_extension"}, 422)
            try:
                pack.validate_schema("offer", body["ext"])
            except ValidationError, Unresolvable:
                return JSONResponse({"error": "schema_invalid"}, 422)
        # An offer from the room is what the member chose to share (private ext fields are
        # refused above), so the coalition sees it; host-only offers would scope every plan
        # built from them to the host, and nobody could see or approve a plan.
        envelope = build_envelope(
            person, coalition, "coalition.offer", payload, scope={"audience": "coalition"}
        )
        reply = await server.ports[coalition].accept(envelope, person.card_url)
        if "error" in reply:
            return JSONResponse({"error": reply["error"]["code"]}, 422)
        return JSONResponse(
            {"seq": reply["receipt"]["payload"]["seq"], "offer_id": payload["offer_id"]}
        )

    @app.get("/v1/agent/vault")
    def vault_keys(who: Viewer, request: Request) -> Document:
        if request.query_params:
            raise HTTPException(403, "vault belongs to the viewer")
        hosted(who)
        return {"keys": sorted(server.registry.vault_values(coalition, who))}

    @app.post("/v1/agent/vault")
    def vault_save(body: Document, who: Viewer, request: Request) -> Document:
        if request.query_params or set(body) - {"values"}:
            raise HTTPException(403, "vault belongs to the viewer")
        hosted(who)
        if not isinstance(body.get("values"), dict):
            raise HTTPException(422, "values must be an object")
        return {"keys": sorted(server.registry.vault_values(coalition, who, body["values"]))}
