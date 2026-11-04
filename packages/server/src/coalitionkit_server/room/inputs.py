# SPDX-License-Identifier: Apache-2.0
"""Phone inputs: a spoken clip or a photo becomes words the person confirms.

``POST /v1/room/voice`` transcribes a short WAV and ``POST /v1/room/photo`` reads an image against
one of the viewer's own brief questions (or for a sentence to say). Neither saves anything the
room acts on: the person sees the words, may change them, and confirms them through the existing
routes (``/v1/room/brief`` for an answer, ``/v1/room/say`` for a sentence). The audio and image
bytes live in memory for the call only; they never enter the log or the store. What the person
read back is kept in their own vault under ``_room_inputs`` for their own screen.

Each media or model call is reported through an optional ``on_activity`` callback with the shared
activity shape; its ``args`` and ``result`` never hold what was said or seen.
"""

from __future__ import annotations

import time
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, HTTPException, Request
from starlette.datastructures import UploadFile
from starlette.responses import JSONResponse

from coalitionkit_models import BudgetExhaustedError, MissingKeyError, ProviderError
from coalitionkit_models.errors import MediaInputError
from coalitionkit_models.media import MediaClient, image_mime
from coalitionkit_models.wav import validate_wav
from coalitionkit_surfaces.app import Viewer

from ..adapter import Document
from . import inputs_read
from .needs import tidy

if TYPE_CHECKING:
    from ..app import Server
    from .engine import RoomEngine

ActivityHook = Callable[[dict[str, Any]], Awaitable[None]]

INPUTS = "_room_inputs"
KEEP = 10
MAX_CLIP_MS = 20_000
MAX_AUDIO_BYTES = 2 * 1024 * 1024
MAX_IMAGE_BYTES = 8 * 1024 * 1024
IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}
TEXT_MAX = 500


async def upload(request: Request, field: str, limit: int) -> tuple[bytes, dict[str, str]]:
    """The uploaded bytes and the plain fields: a multipart part named ``field``, or the raw body
    with its fields in the query string. Refused with 413 above ``limit``."""
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > limit + 64 * 1024:
        raise HTTPException(413, "the upload is too large")
    fields = {k: v for k, v in request.query_params.items()}
    if request.headers.get("content-type", "").startswith("multipart/form-data"):
        async with request.form(max_files=1, max_fields=4, max_part_size=limit) as form:
            part = form.get(field)
            if not isinstance(part, UploadFile):
                raise HTTPException(422, f"send the {field} as a file part named {field!r}")
            data = await part.read(limit + 1)
            fields.update({k: v for k, v in form.items() if isinstance(v, str)})
    else:
        chunks: list[bytes] = []
        size = 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > limit:
                raise HTTPException(413, "the upload is too large")
            chunks.append(chunk)
        data = b"".join(chunks)
    if len(data) > limit:
        raise HTTPException(413, "the upload is too large")
    if not data:
        raise HTTPException(422, f"send the {field}")
    return data, fields


def remember(engine: RoomEngine, coalition: str, who: str, kind: str, text: str, ms: int) -> None:
    """What the person's input read as, for their own screen only."""
    if not text:
        return
    with engine.lock:
        kept = list(engine.vault(coalition, who).get(INPUTS, []))
        at = datetime.fromtimestamp(engine.now(), UTC).isoformat()
        item = {"kind": kind, "text": tidy(text, TEXT_MAX), "ms": ms, "at": at}
        try:
            engine.vault_put(coalition, who, INPUTS, [*kept, item][-KEEP:])
        except ValueError:
            return  # a seat with no hosted vault here (an agent it brought) keeps nothing
    engine.bump(coalition)


def inputs_of(engine: RoomEngine, coalition: str, viewer: str) -> list[Document]:
    """``room.mine.inputs``: the viewer's own recent voice and photo readings, oldest first."""
    kept: list[Document] = engine.vault(coalition, viewer).get(INPUTS, [])
    return [{"kind": i["kind"], "text": i["text"], "ms": i["ms"]} for i in kept]


@asynccontextmanager
async def reported(
    hook: ActivityHook | None, seat: str, tool: str, args: str
) -> AsyncGenerator[Document]:
    """Report a call as started, then done or failed with its time. The block sets ``result``."""
    line: Document = {"result": ""}
    refs: list[str] = []
    base: Document = {"seat": seat, "agent": "phone", "tool": tool, "args": args, "refs": refs}
    if hook is not None:
        await hook({**base, "result": "", "status": "started", "ms": 0})
    started = time.monotonic()
    try:
        yield line
    except BaseException as exc:
        if hook is not None:
            ms = round((time.monotonic() - started) * 1000)
            failed: Document = {**base, "result": type(exc).__name__, "status": "failed", "ms": ms}
            await hook(failed)
        raise
    if hook is not None:
        ms = round((time.monotonic() - started) * 1000)
        await hook({**base, "result": str(line["result"]), "status": "done", "ms": ms})


def media_of(server: Server) -> tuple[MediaClient, bool]:
    """The host's media client, or a fresh one the caller closes (the bool says so)."""
    if server.media is not None:
        return server.media, False
    gateway = server.gateway
    return MediaClient(gateway.settings, meter=gateway.meter), True


def refusal(exc: BaseException) -> HTTPException:
    if isinstance(exc, MissingKeyError | inputs_read.NoKey):
        return HTTPException(503, "this host has no model key for reading voice or photos")
    if isinstance(exc, MediaInputError):
        return HTTPException(422, str(exc))
    if isinstance(exc, BudgetExhaustedError):
        return HTTPException(402, "the room's model budget is spent")
    return HTTPException(502, "the model could not read that; type it instead")


def question_for(engine: RoomEngine, coalition: str, who: str, question_id: str) -> Document:
    try:
        return inputs_read.open_question(engine, coalition, who, question_id)
    except LookupError:
        raise HTTPException(404, "no such question") from None
    except PermissionError:
        raise HTTPException(409, "already answered or closed") from None


async def transcribe(
    server: Server, coalition: str, who: str, wav: bytes, hook: ActivityHook | None
) -> tuple[str, int]:
    media, own = media_of(server)
    started = time.monotonic()
    try:
        async with reported(hook, who, "media:transcribe", "a spoken clip") as line:
            heard = await media.transcribe(wav, coalition_id=coalition, participant=who)
            line["result"] = f"{len(heard.text.split())} words"
    except (MissingKeyError, MediaInputError, BudgetExhaustedError, ProviderError) as exc:
        raise refusal(exc) from None
    except Exception as exc:  # a transport failure the retrier gave up on
        raise refusal(exc) from None
    finally:
        if own:
            await media.aclose()
    return tidy(heard.text, TEXT_MAX), round((time.monotonic() - started) * 1000)


def inputs_routes(
    app: FastAPI, server: Server, coalition: str, on_activity: ActivityHook | None = None
) -> None:
    engine = server.room
    assert engine is not None

    @app.post("/v1/room/voice")
    async def voice(request: Request, who: Viewer) -> JSONResponse:  # pyright: ignore[reportUnusedFunction]
        wav, fields = await upload(request, "audio", MAX_AUDIO_BYTES)
        try:
            length = validate_wav(wav).duration_ms
        except MediaInputError as exc:
            raise HTTPException(422, str(exc)) from None
        if length > MAX_CLIP_MS + 500:
            raise HTTPException(413, "a clip is at most 20 seconds")
        question_id = fields.get("question_id")
        question = question_for(engine, coalition, who, question_id) if question_id else None
        text, ms = await transcribe(server, coalition, who, wav, on_activity)
        del wav  # the audio is never kept
        if not text:
            return JSONResponse({"text": "", "ms": ms, "source": "model"})
        remember(engine, coalition, who, "voice", text, ms)
        body: Document = {"text": text, "ms": ms, "source": "model"}
        if question is not None:
            async with reported(on_activity, who, "model:brief", "spoken answer") as line:
                read, how = await inputs_read.answer_from_words(
                    engine, coalition, who, question, text
                )
                line["result"] = "answer read" if read["answer"] is not None else "no answer"
            body.update(read, question_id=question_id, answer_source=how)
        return JSONResponse(body)

    @app.post("/v1/room/photo")
    async def photo(request: Request, who: Viewer) -> JSONResponse:  # pyright: ignore[reportUnusedFunction]
        image, fields = await upload(request, "image", MAX_IMAGE_BYTES)
        if image_mime(image) not in IMAGE_TYPES:
            raise HTTPException(415, "send a PNG, JPEG or WebP photo")
        question_id, purpose = fields.get("question_id"), fields.get("purpose")
        if bool(question_id) == (purpose == "say"):
            raise HTTPException(422, "send question_id, or purpose 'say'")
        question = question_for(engine, coalition, who, question_id) if question_id else None
        try:
            async with reported(on_activity, who, "model:vision", "a photo") as line:
                if question is not None:
                    read, ms = await inputs_read.answer_from_photo(
                        engine, coalition, who, question, image
                    )
                else:
                    read, ms = await inputs_read.say_from_photo(engine, coalition, who, image)
                line["result"] = "answer read" if read["answer"] is not None else "no answer"
        except inputs_read.Unreadable as exc:
            raise refusal(exc) from None
        finally:
            del image  # the photo is never kept
        remember(engine, coalition, who, "photo", read["words"] or read["description"], ms)
        body: Document = {**read, "ms": ms, "source": "model"}
        if question_id:
            body["question_id"] = question_id
        return JSONResponse(body)
