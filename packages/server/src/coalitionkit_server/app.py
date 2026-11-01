# SPDX-License-Identifier: Apache-2.0
"""One process for the host, protocol edges, Steward and viewer sessions."""

import asyncio
import json
import secrets
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import cast
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, SecretStr
from starlette.responses import JSONResponse
from starlette.types import Receive, Scope, Send

from coalitionkit_contracts import new_ulid, public_key_to_jwk, validate_payload
from coalitionkit_edges.a2a import HostSigner, create_host_app
from coalitionkit_mcp.access import Deps
from coalitionkit_mcp.app import create_app as mcp_app
from coalitionkit_models import ModelGateway
from coalitionkit_models.settings import ROLES
from coalitionkit_runtime import Acknowledgement, CoalitionHost, PostgresStore, SQLiteStore
from coalitionkit_runtime.host import utc_now
from coalitionkit_runtime.pool import PoolBusy, StoreUnavailable
from coalitionkit_steward import Steward
from coalitionkit_surfaces import SurfaceHub
from coalitionkit_surfaces.app import create_app as surfaces_app

from .adapter import Document, HostPort
from .audit import AuditLoop, StewardAdapter, gateway
from .mcp_port import MCPPort
from .packs import install_packs
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

    def attach(self, coalition: str) -> CoalitionHost:
        host = CoalitionHost(
            self.store, coalition, self.signer.card_url, self.key, "host", steward=self.steward
        )
        self.hosts[coalition] = host
        self.ports[coalition] = HostPort(host)
        hub = SurfaceHub(
            host,
            ViewerAuth(self.registry, host),
            lambda participant: OwnerSigner(self.registry, coalition, participant),
        )
        self.surfaces[coalition] = surfaces_app(hub)
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
            path in {"/v1/agent", "/v1/agent/answers"} and "agent" in enabled
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
        Deps(MCPPort(server), ViewPort(server.hosts, server.registry), server.registry),
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
