# SPDX-License-Identifier: Apache-2.0
"""Validate audio before it is sent to the transcriber: mono 16-bit PCM WAV, 16 or 24 kHz."""

from __future__ import annotations

import io
import wave
from dataclasses import dataclass

from .errors import MediaInputError

ALLOWED_RATES = (16_000, 24_000)
MAX_BYTES = 32 * 1024 * 1024
MAX_SECONDS = 600


@dataclass(frozen=True)
class WavInfo:
    sample_rate: int
    frames: int

    @property
    def duration_ms(self) -> int:
        return self.frames * 1000 // self.sample_rate


def validate_wav(data: bytes) -> WavInfo:
    """Raise MediaInputError unless ``data`` is a mono 16-bit PCM WAV at 16 or 24 kHz, at most
    10 minutes and 32 MB."""
    if len(data) > MAX_BYTES:
        raise MediaInputError("audio is larger than 32 MB")
    try:
        with wave.open(io.BytesIO(data), "rb") as reader:
            channels, width = reader.getnchannels(), reader.getsampwidth()
            rate, frames, comp = reader.getframerate(), reader.getnframes(), reader.getcomptype()
    except (wave.Error, EOFError) as exc:
        raise MediaInputError(f"audio is not a readable PCM WAV file ({exc})") from None
    if comp != "NONE":
        raise MediaInputError("audio must be uncompressed PCM")
    if channels != 1:
        raise MediaInputError(f"audio must be mono, got {channels} channels")
    if width != 2:
        raise MediaInputError(f"audio must be 16-bit, got {width * 8}-bit")
    if rate not in ALLOWED_RATES:
        raise MediaInputError(f"audio must be 16 kHz or 24 kHz, got {rate} Hz")
    if frames / rate > MAX_SECONDS:
        raise MediaInputError("audio is longer than 10 minutes")
    return WavInfo(rate, frames)
