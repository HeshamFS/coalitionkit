# SPDX-License-Identifier: Apache-2.0
"""The room's routes for minted devices. Each acts only for the signed-in viewer.

``POST /v1/room/mint`` takes a video and a voice note (multipart) and starts the Mint on the host.
``POST /v1/room/mint/approve`` is the owner's press-and-hold: the host signs the approval with
that person's own key. ``POST /v1/room/mint/frame`` is a camera frame of a seated display device.
Uploaded bytes go to the pipeline's working folder or a temporary file and are removed after use;
they never enter the log or the store.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from starlette.datastructures import UploadFile
from starlette.responses import JSONResponse

from coalitionkit_surfaces.app import Viewer

from . import device_member, device_mint
from .devices import DeviceRefused, is_device
from .seats import read_state

if TYPE_CHECKING:
    from ..app import Server

VIDEO_MAX = 64 * 1024 * 1024
VOICE_MAX = 4 * 1024 * 1024
FRAME_MAX = 8 * 1024 * 1024
LABEL_MAX = 60
DEVICE_PATHS = frozenset({"/v1/room/mint", "/v1/room/mint/approve", "/v1/room/mint/frame"})


class Approve(BaseModel):
    model_config = ConfigDict(extra="forbid")
    device: str = Field(min_length=1, max_length=64)


async def upload(form: Any, name: str, limit: int) -> bytes:
    part = form.get(name)
    if not isinstance(part, UploadFile):
        raise HTTPException(422, f"send {name} as a file")
    data = await part.read(limit + 1)
    if not data or len(data) > limit:
        raise HTTPException(413, f"{name} is empty or too large")
    return data


def device_routes(app: FastAPI, server: Server, coalition: str) -> None:
    engine = server.room
    assert engine is not None

    async def seated_person(who: str) -> None:
        state = await read_state(engine, coalition)
        if who not in state.members or is_device(engine.read(coalition), who):
            raise HTTPException(403, "only a seated person can mint a device")
        if state.stage == "Dissolve":
            raise HTTPException(409, "the room has ended")

    @app.post("/v1/room/mint")
    async def mint_route(request: Request, who: Viewer) -> JSONResponse:
        await seated_person(who)
        async with request.form(max_files=2, max_fields=4) as form:
            video = await upload(form, "video", VIDEO_MAX)
            voice = await upload(form, "voice", VOICE_MAX)
            template = str(form.get("template") or "resource").strip()
            label = str(form.get("label") or "").strip()[:LABEL_MAX]
            needs = [n for n in str(form.get("needs") or "").split(",") if n.strip()]
        if not template or len(template) > 64:
            raise HTTPException(422, "name a Mint template")
        pid = device_mint.start(engine, coalition, who, video, voice, template, label, needs)
        return JSONResponse({"device": pid, "state": "minting"}, 202)

    @app.post("/v1/room/mint/approve")
    async def approve_route(body: Approve, who: Viewer) -> JSONResponse:
        try:
            await device_mint.approve(engine, coalition, who, body.device)
        except device_mint.NotYours:
            raise HTTPException(403, "only the device's owner approves it") from None
        except LookupError:
            raise HTTPException(409, "this device is not waiting for approval") from None
        return JSONResponse({"device": body.device, "state": "seated"})

    @app.post("/v1/room/mint/frame")
    async def frame_route(request: Request, who: Viewer) -> JSONResponse:
        async with request.form(max_files=1, max_fields=2) as form:
            frame = await upload(form, "frame", FRAME_MAX)
            pid = str(form.get("device") or "")
        try:
            read = await device_member.read_frame(engine, coalition, who, pid, frame)
        except PermissionError:
            raise HTTPException(403, "only the device's owner sends its frames") from None
        except LookupError:
            raise HTTPException(409, "this device is not a seated display") from None
        except (DeviceRefused, ValueError) as exc:
            raise HTTPException(422, f"the frame could not be read: {exc}") from None
        return JSONResponse(read)
