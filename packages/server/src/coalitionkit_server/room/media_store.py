# SPDX-License-Identifier: Apache-2.0
"""Pictures a room's agents made, kept on the host and served to that room's viewers only.

Each file sits under the host's data directory at ``media/<coalition>/<sha-256>``; its name is
the hash of its bytes, so a result's data names exactly one picture and cannot be swapped.
``GET /v1/room/media/{hash}`` takes the viewer bearer token of the room and serves only that
room's files. Nothing about a picture enters the log but its hash, alt text, prompt and size.
"""

from __future__ import annotations

import hashlib
import re
import struct
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI, HTTPException
from starlette.responses import Response

from coalitionkit_models.media import image_mime
from coalitionkit_surfaces.app import Viewer

if TYPE_CHECKING:
    from ..app import Server

HASH = re.compile(r"[0-9a-f]{64}")
ROOM = re.compile(r"[A-Za-z0-9_-]{1,64}")
MAX_BYTES = 12 * 1024 * 1024


def media_dir(server: Server, coalition: str) -> Path:
    if not ROOM.fullmatch(coalition):
        raise ValueError("bad coalition id")
    return server.settings.host_key_file.parent / "media" / coalition


def save(server: Server, coalition: str, data: bytes) -> str:
    """Keep the bytes; the answer is their SHA-256, which is also the file's name."""
    if not data or len(data) > MAX_BYTES:
        raise ValueError("no picture, or one too large to keep")
    digest = hashlib.sha256(data).hexdigest()
    folder = media_dir(server, coalition)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / digest
    if not path.exists():
        part = path.with_suffix(".part")
        part.write_bytes(data)
        part.replace(path)
    return digest


def load(server: Server, coalition: str, digest: str) -> bytes | None:
    if not HASH.fullmatch(digest):
        return None
    path = media_dir(server, coalition) / digest
    if not path.is_file():
        return None
    data = path.read_bytes()
    return data if hashlib.sha256(data).hexdigest() == digest else None


def size_of(data: bytes) -> tuple[int, int] | None:
    """Width and height read from a PNG or WebP header; None when it cannot tell."""
    if data.startswith(b"\x89PNG") and len(data) >= 24:
        width, height = struct.unpack(">II", data[16:24])
        return int(width), int(height)
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP" and len(data) >= 30:
        chunk = data[12:16]
        if chunk == b"VP8X":
            width = 1 + int.from_bytes(data[24:27], "little")
            height = 1 + int.from_bytes(data[27:30], "little")
            return width, height
        if chunk == b"VP8 ":
            width, height = struct.unpack("<HH", data[26:30])
            return width & 0x3FFF, height & 0x3FFF
        if chunk == b"VP8L" and len(data) >= 25:
            bits = int.from_bytes(data[21:25], "little")
            return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    return None


def media_routes(app: FastAPI, server: Server, coalition: str) -> None:
    @app.get("/v1/room/media/{digest}")
    async def picture(digest: str, who: Viewer) -> Response:
        del who  # any viewer of this room may see its results; the token is the check
        data = load(server, coalition, digest)
        if data is None:
            raise HTTPException(404, "no such picture in this room")
        return Response(
            data,
            media_type=image_mime(data),
            headers={
                "Cache-Control": "private, max-age=86400",
                "X-Content-Type-Options": "nosniff",
            },
        )
