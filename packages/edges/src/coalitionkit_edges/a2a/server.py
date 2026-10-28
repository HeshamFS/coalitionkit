# SPDX-License-Identifier: Apache-2.0
"""The host's A2A server: a FastAPI app with the host's signed Agent Card and a JSON-RPC endpoint.

One A2A task per exchange. The server assigns task IDs and every message of a Coalition carries
``contextId`` = Coalition ID, so after a task reaches a final state the next message simply
starts a new task in the same context. The authenticated sender comes from the bearer token's
registry entry and never from the payload; the edge hands it to the ``HostPort`` next to the
envelope.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from a2a.auth.user import User
from a2a.helpers.proto_helpers import new_message, new_task_from_user_message
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    DefaultServerCallContextBuilder,
    add_a2a_routes_to_fastapi,
    create_agent_card_routes,
    create_jsonrpc_routes,
)
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
    HTTPAuthSecurityScheme,
    Message,
    SecurityRequirement,
    SecurityScheme,
    StringList,
    TaskState,
)
from fastapi import FastAPI
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from coalitionkit_contracts import is_ulid, new_ulid

from .host_port import HostPort, HostSigner
from .identity import CredentialRegistry, card_key_entry, coalition_extension, sign_card
from .wire import ENVELOPE_MEDIA_TYPE, EXTENSION_URI, envelope_part, message_envelopes

RPC_PATH = "/a2a"
CARD_PATH = "/.well-known/agent-card.json"
_SENDER_KEY = "coalition_sender"
HostIdentity = HostSigner


def build_host_card(
    signer: HostSigner, base_url: str, *, key_not_after: datetime | None = None
) -> AgentCard:
    """The host's Agent Card: JSONRPC at protocol 1.0, the optional extension, signed (JCS, EdDSA).

    The card publishes its own verification key in the extension's ``params.keys``; a member
    pins it from the invitation and never follows a ``jku``.
    """
    key_entry = card_key_entry(signer.private_key.public_key(), signer.kid, key_not_after)
    card = AgentCard(
        name="CoalitionKit host",
        description="Runs Coalitions: orders, authorizes and acknowledges envelopes",
        version="0.1.0",
        supported_interfaces=[
            AgentInterface(
                url=base_url.rstrip("/") + RPC_PATH,
                protocol_binding="JSONRPC",
                protocol_version="1.0",
            )
        ],
        capabilities=AgentCapabilities(
            streaming=False,
            extensions=[
                coalition_extension(
                    {"roles": ["host"], "keys": [key_entry]}, "Hosts multi-party Coalitions"
                )
            ],
        ),
        security_schemes={
            "bearer": SecurityScheme(
                http_auth_security_scheme=HTTPAuthSecurityScheme(scheme="Bearer")
            )
        },
        security_requirements=[SecurityRequirement(schemes={"bearer": StringList(list=[])})],
        default_input_modes=[ENVELOPE_MEDIA_TYPE],
        default_output_modes=[ENVELOPE_MEDIA_TYPE],
        skills=[
            AgentSkill(
                id="coalition-host",
                name="Coalition host",
                description="Accepts Coalition envelopes and acknowledges them with a receipt",
                tags=["coalition"],
            )
        ],
    )
    return sign_card(card, signer.private_key, signer.kid)


class _CardUser(User):
    def __init__(self, card_url: str) -> None:
        self._card_url = card_url

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def user_name(self) -> str:
        return self._card_url


class _SenderContextBuilder(DefaultServerCallContextBuilder):
    """Builds the call context with the user the bearer middleware authenticated."""

    def build_user(self, request: Request) -> User:
        sender = request.scope.get(_SENDER_KEY)
        if isinstance(sender, str):
            return _CardUser(sender)
        return super().build_user(request)


class _BearerMiddleware:
    """Pure ASGI: POSTs to the RPC path need a known bearer token; the card stays public."""

    def __init__(self, app: ASGIApp, credentials: CredentialRegistry) -> None:
        self._app = app
        self._credentials = credentials

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["path"] == RPC_PATH:
            headers = {
                k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]
            }
            scheme, _, token = headers.get("authorization", "").partition(" ")
            sender = (
                self._credentials.authenticate(token.strip())
                if scheme.lower() == "bearer"
                else None
            )
            if sender is None:
                body = b'{"error":"unauthenticated"}'
                await send(
                    {
                        "type": "http.response.start",
                        "status": 401,
                        "headers": [
                            (b"content-type", b"application/json"),
                            (b"content-length", str(len(body)).encode()),
                            (b"www-authenticate", b"Bearer"),
                        ],
                    }
                )
                await send({"type": "http.response.body", "body": body})
                return
            scope[_SENDER_KEY] = sender
        await self._app(scope, receive, send)


class HostExecutor(AgentExecutor):
    """Turns one inbound A2A message into one task that carries the acknowledgement or an error."""

    def __init__(self, host: HostPort, signer: HostSigner) -> None:
        self._host = host
        self._signer = signer

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        message = context.message
        if message is None or context.task_id is None or context.context_id is None:
            return
        if context.current_task is None:
            await event_queue.enqueue_event(new_task_from_user_message(message))
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        user = context.call_context.user
        sender = user.user_name if user.is_authenticated else ""
        state, parts = await self._exchange(context, message, sender)
        reply = new_message([envelope_part(e) for e in parts], context.context_id, context.task_id)
        reply.extensions.append(EXTENSION_URI)
        await updater.update_status(state, reply)

    async def _exchange(
        self, context: RequestContext, message: Message, sender: str
    ) -> tuple[TaskState, list[dict[str, Any]]]:
        context_id = context.context_id or ""
        coalition = context_id if is_ulid(context_id) else new_ulid()
        if EXTENSION_URI not in context.requested_extensions:
            # Coalition data on a call that did not activate the extension is never read.
            return self._rejected(coalition, "extension_not_activated", new_ulid())
        found = message_envelopes(message)
        envelope = found[0] if len(found) == 1 else None
        raw_ref = envelope.get("event_id") if envelope else None
        ref = raw_ref if isinstance(raw_ref, str) and is_ulid(raw_ref) else new_ulid()
        if envelope is None:
            return self._rejected(
                coalition, "schema_invalid", ref, "expected exactly one envelope part"
            )
        if envelope.get("coalition_id") != context_id:
            return self._rejected(
                coalition, "schema_invalid", ref, "contextId must equal coalition_id"
            )
        reply = await self._host.accept(envelope, sender)
        accepted, receipt, error = reply.get("accepted"), reply.get("receipt"), reply.get("error")
        if isinstance(receipt, dict) and (accepted is None or isinstance(accepted, dict)):
            parts = [cast("dict[str, Any]", accepted)] if accepted is not None else []
            return TaskState.TASK_STATE_COMPLETED, [*parts, cast("dict[str, Any]", receipt)]
        if isinstance(error, dict):
            payload = cast("dict[str, Any]", error)
            return TaskState.TASK_STATE_REJECTED, [
                self._signer.envelope(coalition, "coalition.error", payload)
            ]
        return self._rejected(coalition, "schema_invalid", ref, "the host gave no usable reply")

    def _rejected(
        self, coalition: str, code: str, ref: str, text: str | None = None
    ) -> tuple[TaskState, list[dict[str, Any]]]:
        return TaskState.TASK_STATE_REJECTED, [self._signer.error(coalition, code, ref, text)]

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        if context.task_id and context.context_id:
            await TaskUpdater(event_queue, context.task_id, context.context_id).cancel()


def create_host_app(
    host: HostPort,
    signer: HostSigner,
    credentials: CredentialRegistry,
    base_url: str,
    *,
    card: AgentCard | None = None,
) -> FastAPI:
    """The host's FastAPI app: the signed card at the well-known path, JSON-RPC at ``/a2a``."""
    host_card = card if card is not None else build_host_card(signer, base_url)
    handler = DefaultRequestHandler(
        agent_executor=HostExecutor(host, signer),
        task_store=InMemoryTaskStore(),
        agent_card=host_card,
    )
    app = FastAPI(title="CoalitionKit host", docs_url=None, redoc_url=None, openapi_url=None)
    add_a2a_routes_to_fastapi(
        app,
        agent_card_routes=create_agent_card_routes(host_card, card_url=CARD_PATH),
        jsonrpc_routes=create_jsonrpc_routes(
            handler, rpc_url=RPC_PATH, context_builder=_SenderContextBuilder()
        ),
    )
    app.add_middleware(_BearerMiddleware, credentials=credentials)
    return app


__all__ = [
    "CARD_PATH",
    "RPC_PATH",
    "HostExecutor",
    "HostIdentity",
    "build_host_card",
    "create_host_app",
]
