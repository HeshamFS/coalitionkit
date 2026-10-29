# SPDX-License-Identifier: Apache-2.0
"""Parser for the SAM 3.1 text grammar (as documented and as measured live).

One line per frame: ``<Nf>`` then comma-separated records. A record is an ordinal, a box token
and an optional mask token::

    <0f>0<|box;x1=1;y1=2;x2=3;y2=4;w=W;h=H;c=0.97|><|mask;x=0;y=0;c=0.97;data=W,H,~PAYLOAD|>,1<|box...

The box is parsed in full. The mask is kept as the raw payload plus its kind: a payload that
starts with ``~`` is lossless, one that starts with ``!`` is one-bit. ``c=`` (confidence)
appears only when the request asked for it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

MaskKind = Literal["lossless", "one_bit", "unknown"]

_FRAME = re.compile(r"<(\d+)f>")
_HEAD = re.compile(r"(?P<ordinal>\d+)?<\|box;(?P<box>[^|]*)\|>")
_MASK_OPEN = "<|mask;"
_MASK_CLOSE = "|>"


class SamParseError(ValueError):
    """The SAM output does not follow the documented grammar."""


@dataclass(frozen=True)
class Box:
    x1: int
    y1: int
    x2: int
    y2: int
    width: int
    height: int
    confidence: float | None = None


@dataclass(frozen=True)
class Mask:
    """The raw mask payload (everything after ``data=``) and what it is."""

    payload: str
    kind: MaskKind
    width: int
    height: int
    x: int = 0
    y: int = 0


@dataclass(frozen=True)
class Segment:
    box: Box
    mask_payload: str
    ordinal: int
    mask_kind: MaskKind = "unknown"
    mask: Mask | None = None
    frame: int = 0

    @property
    def confidence(self) -> float | None:
        return self.box.confidence


def _pairs(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in text.split(";"):
        if not part:
            continue
        key, sep, value = part.partition("=")
        if not sep:
            raise SamParseError(f"token part {part!r} is not key=value")
        out[key] = value
    return out


def _int(fields: dict[str, str], name: str, token: str) -> int:
    try:
        return int(fields[name])
    except KeyError, ValueError:
        raise SamParseError(f"{token} token lacks integer {name}") from None


def _confidence(fields: dict[str, str]) -> float | None:
    raw = fields.get("c")
    return float(raw) if raw is not None else None


def _parse_box(text: str) -> Box:
    f = _pairs(text)
    return Box(
        _int(f, "x1", "box"),
        _int(f, "y1", "box"),
        _int(f, "x2", "box"),
        _int(f, "y2", "box"),
        _int(f, "w", "box"),
        _int(f, "h", "box"),
        _confidence(f),
    )


def _parse_mask(text: str) -> Mask:
    head, sep, data = text.partition(";data=")
    if not sep:
        raise SamParseError("mask token has no data=")
    f = _pairs(head)
    dims = data.split(",", 2)
    if len(dims) != 3 or not dims[0].isdigit() or not dims[1].isdigit():
        raise SamParseError("mask data does not start with width,height,")
    kind: MaskKind = "unknown"
    if dims[2][:1] == "~":
        kind = "lossless"
    elif dims[2][:1] == "!":
        kind = "one_bit"
    return Mask(data, kind, int(dims[0]), int(dims[1]), _int(f, "x", "mask"), _int(f, "y", "mask"))


def parse_sam_output(text: str) -> list[Segment]:
    """All segments of a SAM response text, in order, across frames."""
    segments: list[Segment] = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        header = _FRAME.match(line)
        if header is None:
            raise SamParseError("a line does not start with a <Nf> frame marker")
        frame = int(header.group(1))
        body = line[header.end() :]
        segments.extend(_parse_frame(frame, body))
    return segments


def _parse_frame(frame: int, body: str) -> list[Segment]:
    """Parse a whole frame body: every character must belong to a record or a separator."""
    out: list[Segment] = []
    pos = 0
    while pos < len(body):
        if out:
            if body[pos] != ",":
                raise SamParseError(f"frame {frame}: unexpected text at offset {pos}")
            pos += 1
        head = _HEAD.match(body, pos)
        if head is None:
            raise SamParseError(f"frame {frame}: no valid box record at offset {pos}")
        pos = head.end()
        mask: Mask | None = None
        if body.startswith(_MASK_OPEN, pos):
            end = body.find(_MASK_CLOSE, pos + len(_MASK_OPEN))
            if end < 0:
                raise SamParseError(f"frame {frame}: unterminated mask at offset {pos}")
            mask = _parse_mask(body[pos + len(_MASK_OPEN) : end])
            pos = end + len(_MASK_CLOSE)
        ordinal = int(head.group("ordinal")) if head.group("ordinal") else len(out)
        out.append(
            Segment(
                _parse_box(head.group("box")),
                mask.payload if mask else "",
                ordinal,
                mask.kind if mask else "unknown",
                mask,
                frame,
            )
        )
    return out
