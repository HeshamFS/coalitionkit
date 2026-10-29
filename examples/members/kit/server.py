# SPDX-License-Identifier: Apache-2.0
"""A member's A2A server: its signed card and a JSON-RPC endpoint the host delivers events to.

One Coalition envelope per A2A message, under the extension header; the bearer token must map
to the host's card URL. The task finishes when the member has handled the event, so the host
learns when a turn (including any model turn and the member's own sends) is over.
"""

from __future__ import annotations

from typing import Any

from a2a.auth.user import User
from a2a.helpers.proto_helpers import new_message, new_task_from_user_message, new_text_part
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
from a2a.types import AgentCard, TaskState
from fastapi import FastAPI
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from coalitionkit_edges.a2a import EXTENSION_URI, CredentialRegistry
from coalitionkit_edges.a2a.server import CARD_PATH, RPC_PATH
from coalitionkit_edges.a2a.wire import message_envelopes

from .core import DeliveryRefused, MemberCore

_CALLER_KEY = "coalition_caller"


class _Caller(User):
    def __init__(self, card_url: str) -> None:
        self._card_url = card_url

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def user_name(self) -> str:
        return self._card_url


class _ContextBuilder(DefaultServerCallContextBuilder):
    def build_user(self, request: Request) -> User:
        caller = request.scope.get(_CALLER_KEY)
        return _Caller(caller) if isinstance(caller, str) else super().build_user(request)


class _Bearer:
    """Pure ASGI: a POST to the RPC path needs a token the member issued; the card is public."""

    def __init__(self, app: ASGIApp, credentials: CredentialRegistry) -> None:
        self._app = app
        self._credentials = credentials

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["path"] == RPC_PATH:
            headers = {
                k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]
            }
            kind, _, token = headers.get("authorization", "").partition(" ")
            caller = (
                self._credentials.authenticate(token.strip()) if kind.lower() == "bearer" else None
            )
            if caller is None:
                body = b'{"error":"unauthenticated"}'
                await send(
                    {
                        "type": "http.response.start",
                        "status": 401,
                        "headers": [
                            (b"content-type", b"application/json"),
                            (b"content-length", str(len(body)).encode()),
                        ],
                    }
                )
                await send({"type": "http.response.body", "body": body})
                return
            scope[_CALLER_KEY] = caller
        await self._app(scope, receive, send)


class MemberExecutor(AgentExecutor):
    def __init__(self, core: MemberCore, host_card_url: str) -> None:
        self._core = core
        self._host_card_url = host_card_url

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        message = context.message
        if message is None or context.task_id is None or context.context_id is None:
            return
        if context.current_task is None:
            await event_queue.enqueue_event(new_task_from_user_message(message))
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        state, text = await self._handle(context, message)
        reply = new_message([new_text_part(text)], context.context_id, context.task_id)
        await updater.update_status(state, reply)

    async def _handle(self, context: RequestContext, message: Any) -> tuple[TaskState, str]:
        user = context.call_context.user
        if not user.is_authenticated or user.user_name != self._host_card_url:
            return TaskState.TASK_STATE_REJECTED, "not_authorized: only the host delivers here"
        if EXTENSION_URI not in context.requested_extensions:
            return TaskState.TASK_STATE_REJECTED, "extension_not_activated"
        found = message_envelopes(message)
        if len(found) != 1:
            return TaskState.TASK_STATE_REJECTED, "schema_invalid: expected one envelope part"
        try:
            return TaskState.TASK_STATE_COMPLETED, await self._core.handle(found[0])
        except DeliveryRefused as exc:
            return TaskState.TASK_STATE_REJECTED, str(exc)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        if context.task_id and context.context_id:
            await TaskUpdater(event_queue, context.task_id, context.context_id).cancel()


def create_member_app(
    core: MemberCore, card: AgentCard, host_tokens: CredentialRegistry
) -> FastAPI:
    """The member's FastAPI app: its signed card at the well-known path, JSON-RPC at /a2a."""
    handler = DefaultRequestHandler(
        agent_executor=MemberExecutor(core, core.invitation.host_card_url),
        task_store=InMemoryTaskStore(),
        agent_card=card,
    )
    app = FastAPI(title="Coalition member", docs_url=None, redoc_url=None, openapi_url=None)
    add_a2a_routes_to_fastapi(
        app,
        agent_card_routes=create_agent_card_routes(card, card_url=CARD_PATH),
        jsonrpc_routes=create_jsonrpc_routes(
            handler, rpc_url=RPC_PATH, context_builder=_ContextBuilder()
        ),
    )
    app.add_middleware(_Bearer, credentials=host_tokens)
    return app
