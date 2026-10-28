# SPDX-License-Identifier: Apache-2.0
"""The CoalitionKit MCP server: any MCP host joins a Coalition with an A2A member's rights."""

from .access import Deps
from .app import create_app
from .ports import HostedParticipant, TokenPort, ViewPort
from .server import build_server
from .tools_read import VIEW_URI

__all__ = [
    "VIEW_URI",
    "Deps",
    "HostedParticipant",
    "TokenPort",
    "ViewPort",
    "build_server",
    "create_app",
]
