# SPDX-License-Identifier: Apache-2.0
"""One process for the host, protocol edges, Steward and viewer sessions."""

import asyncio
import json
import secrets
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from jsonschema.exceptions import ValidationError
from pydantic import BaseModel, SecretStr
from referencing.exceptions import Unresolvable
from starlette.responses import JSONResponse
from starlette.types import Receive, Scope, Send

from coalitionkit_contracts import (
    SchemaValidationError,
    new_ulid,
    public_key_to_jwk,
    validate_payload,
)
from coalitionkit_contracts.payloads import Window
from coalitionkit_edges.a2a import HostSigner, create_host_app
from coalitionkit_edges.a2a.identity import CardError
from coalitionkit_gardener import build_propose
from coalitionkit_mcp.access import Deps
from coalitionkit_mcp.app import create_app as mcp_app
from coalitionkit_mcp.gateway import build_envelope
from coalitionkit_models import ModelGateway
from coalitionkit_models.settings import ROLES
from coalitionkit_packs import Pack
from coalitionkit_packs.views import extend_catalog
from coalitionkit_runtime import Acknowledgement, CoalitionHost, PostgresStore, SQLiteStore
from coalitionkit_runtime.host import utc_now
from coalitionkit_runtime.pool import PoolBusy, StoreUnavailable
from coalitionkit_steward import Steward
from coalitionkit_surfaces import SurfaceHub, load_catalog
from coalitionkit_surfaces.app import Viewer
from coalitionkit_surfaces.app import create_app as surfaces_app

from .adapter import Document, HostPort
from .audit import AuditLoop, StewardAdapter, gateway
from .mcp_port import MCPPort
from .packs import (
    bind_runtime,
    install_packs,
    mint_templates,
    plan_for,
    private_extension,
    surface_pack,
    viewer_schema,
)
from .registry import Registry
from .settings import Settings, load_key
from .views import OwnerSigner, ViewerAuth, ViewPort
from .whatsapp import mount_whatsapp


class Server:
    def __init__(self, settings: Settings, model_gateway: ModelGateway | None = None) -> None:
        self.settings = settings
        self.packs = install_packs(
            settings.packs, settings.catalog_file, settings.pack_trusted_keys
        )
        self.key = load_key(settings.host_key_file)
        url = settings.store.get_secret_value()
        if url.startswith("sqlite:///"):
            path = url.removeprefix("sqlite:///")
            if path != ":memory:":
                Path(path).parent.mkdir(parents=True, exist_ok=True)
            self.store = SQLiteStore(path)
        elif url.startswith(("postgresql://", "postgres://")):
            self.store = PostgresStore(url)
        else:
            raise ValueError("store must be sqlite:///path or a Postgres URL")
        self.gateway = model_gateway or gateway()
        self.runner = AuditLoop()
        self.steward = StewardAdapter(
            lambda: Steward(self.gateway, signing_key=self.key, kid="host"),
            self.runner,
        )
        self.signer = HostSigner(
            settings.public_base_url + "/.well-known/agent-card.json", self.key, "host"
        )
        self.hosts: dict[str, CoalitionHost] = {}
        self.ports: dict[str, HostPort] = {}
        self.surfaces: dict[str, FastAPI] = {}
        self.registry = Registry(self.store, self.key, settings.public_base_url)
        with self.store.transaction("") as tx:
            rows = tx.execute("SELECT id, host FROM coalitions").fetchall()
        for coalition, card_url in rows:
            if card_url != self.signer.card_url:
                raise ValueError("public base URL differs from the stored host identity")
            self.attach(coalition)
        self.registry.restore(self.ports)

    def bound_pack(self, coalition: str) -> Pack | None:
        ref = self.hosts[coalition].state.charter.get("pack")
        return self.packs.get((ref["name"], ref["version"])) if ref else None

    def mint_templates(self, coalition: str) -> Any:
        pack = self.bound_pack(coalition)
        if pack is None:
            raise ValueError("Coalition has no bound pack")
        return mint_templates(pack, coalition, self.settings.pack_trusted_keys)

    def enroll_minted(self, coalition: str, minted: Any) -> Document:
        """Registration seam: proof and owner approval precede business-card admission."""
        import importlib

        artifact = importlib.import_module("coalitionkit_mint.artifact")
        if minted.coalition_id != coalition or not minted.template_name:
            raise ValueError("Mint artifact belongs to another Coalition")
        entry = self.mint_templates(coalition).resolve(coalition, minted.template_name)
        config, _, digest = artifact.load(minted.folder)
        if (
            digest != minted.manifest_hash
            or config != entry.config()
            or not minted.attacks
            or not all(a.passed for a in minted.attacks)
        ):
            raise ValueError("Mint proof does not match the bound template")
        card = json.loads((minted.folder / "agent-card.json").read_text(encoding="utf-8"))
        invite = self.registry.issue_invitation(coalition, "business")
        return self.registry.redeem(
            invite["link"].split("#", 1)[1], self.ports, minted.sandbox.url, card
        )

    def attach(self, coalition: str) -> CoalitionHost:
        host = CoalitionHost(
            self.store, coalition, self.signer.card_url, self.key, "host", steward=self.steward
        )
        bind_runtime(host, self.packs)
        self.hosts[coalition] = host
        self.ports[coalition] = HostPort(host)
        core_catalog = load_catalog(self.settings.catalog_file) if self.packs else None

        def pack_state() -> Document | None:
            pack = self.bound_pack(coalition)
            return surface_pack(pack) if pack else None

        hub = SurfaceHub(
            host,
            ViewerAuth(self.registry, host),
            lambda participant: OwnerSigner(self.registry, coalition, participant),
            catalog=core_catalog,
            pack_state=pack_state,
            pack_catalog=lambda: (
                extend_catalog(
                    core_catalog, [pack.components] if (pack := self.bound_pack(coalition)) else []
                )
                if core_catalog
                else None
            ),
            pack_views=lambda: pack.views.order if (pack := self.bound_pack(coalition)) else {},
        )

        def policy_escalation(event: Document, policy_id: str, explain: str) -> None:
            hub.say(
                event["on_behalf_of"],
                json.dumps(
                    {
                        "policy_review": {
                            "policy_id": policy_id,
                            "explain": explain,
                            "question": "Please review, revise and resend.",
                        }
                    }
                ),
            )

        host.policy_escalation = policy_escalation
        self.surfaces[coalition] = surfaces_app(hub)
        hosted_routes(self.surfaces[coalition], self, coalition)
        self.ports[coalition].on_refusal = hub.refused
        return host

    def create(self, charter: Document) -> Document:
        validate_payload("coalition.charter", {**charter, "created_at": utc_now(), "revision": 1})
        coalition = new_ulid()
        host = self.attach(coalition)
        host.create()
        result = host.host_emit("charter", charter, {"audience": "coalition"})
        if not isinstance(result, Acknowledgement):
            raise ValueError("charter refused: " + result["payload"]["code"])
        invites = [
            {"participant": participant, "invitation": self.registry.issue(coalition, participant)}
            for participant in charter["deciders"]
        ]
        return {
            "coalition_id": coalition,
            "invitations": invites,
            "host_key": public_key_to_jwk(self.key.public_key(), "host"),
            "host_card_url": self.signer.card_url,
        }

    def plan(self, coalition: str, deadline: str) -> Acknowledgement | Document:
        host = self.hosts[coalition]
        plans = plan_for(host, self.packs)
        if not plans.plans:
            return {"unresolved": [item.reason for item in plans.unresolved]}
        payload = build_propose(plans, deadline=deadline, proposal_set_id=new_ulid())
        sources = [
            e["event_id"]
            for e in host.state.events.values()
            if e["type"] in {"coalition.need", "coalition.offer"}
        ]
        return host.host_emit("propose", payload.to_wire(), sources=sources)

    def vault_result_sink(
        self, coalition: str, participant: str, match_id: str
    ) -> Callable[[list[str] | int], None]:
        """Bind a hosted Requester's on_result to its owner's private agent channel.

        Hosted runners pass this callback when constructing the PSI Requester.
        There is no protocol event: neither the log nor Steward sees the result.
        """
        self.registry.hosted_for(coalition, participant)
        hub: SurfaceHub = self.surfaces[coalition].state.hub

        def deliver(result: list[str] | int) -> None:
            body: Document = {"match_id": match_id}
            if isinstance(result, int):
                body["count"] = result
            else:
                body.update(overlap=result, count=len(result))
            hub.say(participant, json.dumps({"vault_result": body}))

        return deliver

    async def skills(self, participant: str, coalition_id: str) -> list[Document]:
        if not await ViewPort(self.hosts, self.registry).is_member(participant, coalition_id):
            return []
        return self.hosts[coalition_id].skills(participant)

    async def accept(self, envelope_json: Document, authenticated_sender: str) -> Document:
        port = self.ports.get(str(envelope_json.get("coalition_id", "")))
        if port is None:
            return {"error": {"code": "unknown_participant", "detail": {}, "ref": new_ulid()}}
        return await port.accept(envelope_json, authenticated_sender)

    def close(self) -> None:
        self.runner.close()
        self.store.close()


class Redeem(BaseModel):
    invitation: SecretStr
    card_url: str | None = None
    card: Document | None = None


class Invitation(BaseModel):
    participant: str


def admin(request: Request, settings: Settings) -> None:
    expected = settings.admin_token
    value = request.headers.get("authorization", "").removeprefix("Bearer ")
    if expected is None or not secrets.compare_digest(value, expected.get_secret_value()):
        raise HTTPException(401, "admin authentication required")


def admin_routes(app: FastAPI, server: Server) -> None:
    @app.post("/admin/coalitions/{coalition}/host-events")
    def emit(request: Request, coalition: str, body: Document) -> Document:  # pyright: ignore[reportUnusedFunction]
        admin(request, server.settings)
        if coalition not in server.hosts:
            raise HTTPException(404)
        if (
            set(body) - {"type", "payload", "scope", "sources"}
            or not isinstance(body.get("type"), str)
            or not isinstance(body.get("payload"), dict)
            or (body.get("scope") is not None and not isinstance(body["scope"], dict))
            or (
                "sources" in body
                and (
                    not isinstance(body["sources"], list)
                    or not all(
                        isinstance(source, str) for source in cast(list[object], body["sources"])
                    )
                )
            )
        ):
            raise HTTPException(422, "invalid host event request")
        reply = server.hosts[coalition].host_emit(
            body["type"], body["payload"], body.get("scope"), sources=body.get("sources")
        )
        if isinstance(reply, Acknowledgement):
            return {"accepted": reply.accepted, "receipt": reply.receipt}
        return reply

    @app.post("/admin/coalitions")
    def create(request: Request, charter: Document) -> Document:  # pyright: ignore[reportUnusedFunction]
        admin(request, server.settings)
        try:
            return server.create(charter)
        except ValueError:
            raise HTTPException(422, "charter refused") from None

    @app.post("/admin/coalitions/{coalition}/invitations")
    def invite(request: Request, coalition: str, body: Invitation) -> Document:  # pyright: ignore[reportUnusedFunction]
        admin(request, server.settings)
        if coalition not in server.hosts:
            raise HTTPException(404)
        return {"invitation": server.registry.issue(coalition, body.participant)}

    @app.post("/admin/coalitions/{coalition}/connectors")
    def connector_invite(request: Request, coalition: str, body: Document) -> Document:
        admin(request, server.settings)
        if coalition not in server.hosts:
            raise HTTPException(404)
        pack = server.bound_pack(coalition)
        if (
            pack is None
            or body.get("pack") != {"name": pack.name, "version": pack.manifest.version}
            or body.get("connector") not in {c.name for c in pack.manifest.connectors or []}
        ):
            raise HTTPException(422, "connector is not declared by this Coalition's pack")
        invite = server.registry.issue_invitation(coalition, "business")
        return {"invitation": invite["link"]}

    @app.get("/admin/status")
    def status(request: Request) -> Document:  # pyright: ignore[reportUnusedFunction]
        admin(request, server.settings)
        return {
            "coalitions": [
                {
                    "coalition_id": cid,
                    "members": len(host.state.members),
                    "events": len(server.store.read(cid)),
                }
                for cid, host in server.hosts.items()
            ]
        }

    @app.post("/invitations/redeem")
    def redeem(body: Redeem) -> Document:  # pyright: ignore[reportUnusedFunction]
        try:
            return server.registry.redeem(
                body.invitation.get_secret_value(), server.ports, body.card_url, body.card
            )
        except CardError as exc:
            raise HTTPException(400, "card refused: " + exc.reason) from None
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None
        except Exception:
            raise HTTPException(400, "invitation or card refused") from None

    @app.get("/cards/{coalition}/{participant}")
    def card(coalition: str, participant: str) -> Document:  # pyright: ignore[reportUnusedFunction]
        with server.store.transaction(coalition) as tx:
            row = tx.execute(
                "SELECT card FROM server_credentials "
                "WHERE coalition = ? AND participant = ? AND hosted != ''",
                (coalition, participant),
            ).fetchone()
        if row is None:
            raise HTTPException(404)
        return json.loads(row[0])


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
        envelope = build_envelope(person, coalition, "coalition.offer", payload)
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


class Dispatch:
    def __init__(self, server: Server, mcp: FastAPI) -> None:
        self.server, self.mcp = server, mcp

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope["path"]
        enabled = self.server.settings.surfaces
        if path == "/mcp" and "mcp" in enabled:
            await self.mcp(scope, receive, send)
            return
        allowed = (path in {"/v1/feed", "/v1/view-as"} and "feed" in enabled) or (
            path in {"/v1/agent", "/v1/agent/answers", "/v1/agent/offer", "/v1/agent/vault"}
            and "agent" in enabled
        )
        if not allowed:
            await JSONResponse({"detail": "not found"}, 404)(scope, receive, send)
            return
        request = Request(scope)
        token = request.headers.get("authorization", "").removeprefix("Bearer ")
        row = self.server.registry.lookup(token)
        if row is None:
            await JSONResponse({"detail": "unauthenticated"}, 401)(scope, receive, send)
            return
        await self.server.surfaces[row["coalition"]](scope, receive, send)


def create_server(settings: Settings, model_gateway: ModelGateway | None = None) -> FastAPI:
    """The composed application. ``model_gateway`` is a test hook for metered gateways."""
    server = Server(settings, model_gateway)
    mcp = mcp_app(
        Deps(
            MCPPort(server), ViewPort(server.hosts, server.registry), server.registry, skills=server
        ),
        public_url=settings.public_base_url + "/mcp",
        issuer_url=settings.public_base_url,
        allowed_hosts=[urlsplit(settings.public_base_url).netloc],
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
        whatsapp = getattr(app.state, "whatsapp", None)
        if whatsapp is not None:
            whatsapp.start()
        try:
            async with mcp.router.lifespan_context(mcp):
                yield
        finally:
            if whatsapp is not None:
                await asyncio.to_thread(whatsapp.stop)
            await asyncio.to_thread(server.close)

    app = create_host_app(server, server.signer, server.registry, settings.public_base_url)
    app.router.lifespan_context = lifespan
    app.state.server = server
    admin_routes(app, server)
    from .genesis import mount_genesis

    mount_genesis(app, server)

    @app.get("/healthz", response_model=None)
    def health() -> Document | JSONResponse:  # pyright: ignore[reportUnusedFunction]
        try:
            with server.store.transaction("") as tx:
                tx.execute("SELECT 1")
        except PoolBusy:
            return JSONResponse({"status": "unavailable", "store": "busy"}, status_code=503)
        except StoreUnavailable:
            return JSONResponse({"status": "unavailable", "store": "down"}, status_code=503)
        routes: dict[str, str] = {}
        for role in ROLES:
            try:
                server.gateway.settings.api_key(server.gateway.settings.route(role))
            except Exception:
                routes[role] = "missing_key"
            else:
                routes[role] = "configured_not_probed"
        steward = server.gateway.settings.route("steward")
        steward_status = {
            "provider": server.gateway.settings.steward_host,
            "model": steward.model,
            "fallback": server.gateway.settings.steward_host == "meta",
        }
        return {"status": "ok", "store": "ok", "model_routes": routes, "steward": steward_status}

    mount_whatsapp(
        app,
        settings,
        server.store,
        server.hosts,
        lambda request: admin(request, settings),
        server.registry.lookup,
    )
    app.mount("/", Dispatch(server, mcp))
    return app
