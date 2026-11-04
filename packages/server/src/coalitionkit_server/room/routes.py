# SPDX-License-Identifier: Apache-2.0
"""The room's HTTP routes for the signed-in viewer: begin and answer the brief.

They live on the per-coalition surfaces app beside ``hosted_routes``, behind ``Dispatch`` with
the ``agent`` surface. Each acts only for the authenticated viewer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict
from starlette.responses import JSONResponse

from coalitionkit_surfaces.app import Viewer

from ..adapter import Document
from . import brief, say, seats, work
from .device_routes import device_routes
from .media_store import media_routes
from .view import phase_of

if TYPE_CHECKING:
    from ..app import Server


class Begin(BaseModel):
    model_config = ConfigDict(extra="forbid")
    helpers: bool = False


class Say(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str
    via: Literal["typed", "voice", "photo"] = "typed"


class Done(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_id: str


class Answer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question_id: str
    value: Any = None
    skip: bool = False


def room_routes(app: FastAPI, server: Server, coalition: str) -> None:
    engine = server.room
    assert engine is not None
    media_routes(app, server, coalition)

    @app.post("/v1/room/begin")
    async def begin(body: Begin, who: Viewer) -> JSONResponse:
        if who != engine.owner(coalition):
            raise HTTPException(403, "only the owner can begin the room")
        async with engine.lock_for(coalition):
            doc = engine.read(coalition)
            if doc["needs_state"] != "ready":
                return JSONResponse({"error": "needs_not_ready"}, 409)
            if not doc["begun"]:
                try:
                    await seats.request_begin(engine, coalition, helpers=body.helpers, auto=False)
                except RuntimeError:
                    # The step that follows picks up where this stopped.
                    engine.wake(coalition)
            state = await seats.read_state(engine, coalition)
            return JSONResponse({"phase": phase_of(state, engine.read(coalition))})

    @app.post("/v1/room/say")
    async def say_route(body: Say, who: Viewer) -> JSONResponse:
        text = body.text.strip()
        if not text or len(text) > say.MAX_SAY:
            raise HTTPException(422, f"say something, up to {say.MAX_SAY} characters")
        source = {"voice": "voice", "photo": "camera"}.get(body.via, "chat")
        return JSONResponse(await say.say(engine, coalition, who, text, source=source))

    @app.post("/v1/room/done")
    async def done_route(body: Done, who: Viewer) -> JSONResponse:
        try:
            sent = await work.mark_done(engine, coalition, who, body.task_id)
        except LookupError:
            raise HTTPException(409, "your approved commitment has no result to finish") from None
        if sent is None:
            return JSONResponse({"error": "stopped"}, 409)
        return JSONResponse({"seq": sent["seq"]})

    @app.post("/v1/room/brief")
    async def answer(body: Answer, who: Viewer) -> JSONResponse:
        skip = body.skip is True
        if skip == (body.value is not None):
            raise HTTPException(422, "send a value, or skip")
        try:
            status = brief.answer(engine, coalition, who, body.question_id, body.value, skip)
        except brief.UnknownQuestion:
            raise HTTPException(404, "no such question") from None
        except brief.BriefClosed:
            raise HTTPException(409, "already answered or closed") from None
        except ValueError:
            raise HTTPException(422, "the answer does not fit the question") from None
        result: Document = {"status": status}
        return JSONResponse(result)

    device_routes(app, server, coalition)
