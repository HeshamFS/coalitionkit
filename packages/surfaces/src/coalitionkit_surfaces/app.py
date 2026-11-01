# SPDX-License-Identifier: Apache-2.0
"""The FastAPI app: two SSE endpoints and one POST for consent answers."""

from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from .agent import ConsentError
from .hub import SurfaceHub

SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
STATUS = {
    "not_your_request": 403,
    "unknown_request": 404,
    "not_open": 409,
    "stale_subject": 409,
    "not_authorized": 409,
    "choice_required": 422,
    "bad_choice": 422,
    "signer_mismatch": 502,
    "bad_signature": 502,
}


class AnswerBody(BaseModel):
    interrupt_id: str
    consent: bool
    choice: str | None = None


def _viewer(request: Request, authorization: Annotated[str | None, Header()] = None) -> str:
    hub: SurfaceHub = request.app.state.hub
    scheme, _, token = (authorization or "").partition(" ")
    who = hub.auth.viewer_for(token) if scheme.lower() == "bearer" and token else None
    if who is None:
        raise HTTPException(401, "a valid viewer token is required")
    return who


Viewer = Annotated[str, Depends(_viewer)]


def create_app(hub: SurfaceHub) -> FastAPI:
    app = FastAPI(title="CoalitionKit surfaces", docs_url=None, redoc_url=None)
    app.state.hub = hub

    @app.get("/v1/view-as")
    def view_as(who: Viewer, participant: str) -> JSONResponse:  # pyright: ignore[reportUnusedFunction]
        try:
            return JSONResponse({"messages": hub.view_as(who, participant)})
        except KeyError:
            raise HTTPException(404, "unknown participant") from None

    @app.get("/v1/feed")
    async def feed(who: Viewer) -> StreamingResponse:  # pyright: ignore[reportUnusedFunction]
        return StreamingResponse(
            hub.stream(hub.feed_session(who), who),
            media_type="text/event-stream",
            headers=SSE_HEADERS,
        )

    @app.get("/v1/agent")
    async def agent(who: Viewer) -> StreamingResponse:  # pyright: ignore[reportUnusedFunction]
        return StreamingResponse(
            hub.stream(hub.agent_session(who), who),
            media_type="text/event-stream",
            headers=SSE_HEADERS,
        )

    @app.post("/v1/agent/answers")
    def answer(body: AnswerBody, who: Viewer) -> JSONResponse:  # pyright: ignore[reportUnusedFunction]
        try:
            result = hub.agent_session(who).answer(body.interrupt_id, body.consent, body.choice)
        except ConsentError as exc:
            return JSONResponse(
                {"error": exc.code, "detail": exc.detail}, STATUS.get(exc.code, 400)
            )
        return JSONResponse(result)

    return app
