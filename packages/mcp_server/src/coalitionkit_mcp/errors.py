# SPDX-License-Identifier: Apache-2.0
"""Errors a tool or resource can end in. Each carries a ``coalition.error`` code."""

from __future__ import annotations

import re
from typing import Final, get_args

from mcp.server.mcpserver.exceptions import ResourceError, ToolError

from coalitionkit_contracts.payloads import ErrorCode

ERROR_CODES: Final[frozenset[str]] = frozenset(get_args(ErrorCode))
_CODE_IN_TEXT = re.compile(r"\b(" + "|".join(sorted(ERROR_CODES)) + r"): ([^\n]*)")


class CoalitionToolError(ToolError):
    """A tool failed with a ``coalition.error`` code; the message reads ``<code>: <detail>``."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


class CoalitionResourceError(ResourceError):
    """A resource read was refused with a ``coalition.error`` code."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def split_error_text(text: str) -> tuple[str, str] | None:
    """The ``(code, detail)`` an error text carries, or None when it names no known code."""
    found = _CODE_IN_TEXT.search(text)
    return (found.group(1), found.group(2).strip()) if found else None
