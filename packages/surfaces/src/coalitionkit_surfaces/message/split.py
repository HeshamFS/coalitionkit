# SPDX-License-Identifier: Apache-2.0
"""Split text into messages of at most ``limit`` characters, on paragraph, line, word edges."""

from __future__ import annotations

from collections.abc import Sequence

DEFAULT_LIMIT = 1000
MIN_LIMIT = 40


def _mark(index: int, total: int) -> str:
    return f" ({index}/{total})"


def _break(text: str, limit: int) -> list[str]:
    """Pieces of one long block: lines first, then words, then a hard cut."""
    pieces: list[str] = []
    for line in text.split("\n"):
        if len(line) <= limit:
            pieces.append(line)
            continue
        current = ""
        for word in line.split(" "):
            while len(word) > limit:
                if current:
                    pieces.append(current)
                    current = ""
                pieces.append(word[:limit])
                word = word[limit:]
            joined = f"{current} {word}" if current else word
            if len(joined) > limit:
                pieces.append(current)
                current = word
            else:
                current = joined
        if current:
            pieces.append(current)
    return pieces


def _layout(blocks: Sequence[str], limit: int) -> list[str]:
    """Pack blocks (paragraphs) greedily; a block that does not fit is broken by lines."""
    parts: list[str] = []
    current = ""
    for block in blocks:
        if not block:
            continue
        for piece, glue in (
            [(block, "\n\n")] if len(block) <= limit else [(p, "\n") for p in _break(block, limit)]
        ):
            joined = f"{current}{glue}{piece}" if current else piece
            if len(joined) > limit:
                parts.append(current)
                current = piece
            else:
                current = joined
    if current:
        parts.append(current)
    return parts


def split_blocks(blocks: Sequence[str], limit: int = DEFAULT_LIMIT) -> list[str]:
    """Messages no longer than ``limit``; a split set carries ``(i/n)`` at the end of each part."""
    if limit < MIN_LIMIT:
        raise ValueError(f"message limit must be at least {MIN_LIMIT}")
    parts = _layout(blocks, limit)
    if len(parts) <= 1:
        return parts
    count = len(parts)
    while True:  # the suffix width depends on the page count, which depends on the width
        width = len(_mark(count, count))
        parts = _layout(blocks, limit - width)
        if len(_mark(len(parts), len(parts))) <= width:
            break
        count = len(parts)
    total = len(parts)
    return [f"{part}{_mark(index, total)}" for index, part in enumerate(parts, start=1)]
