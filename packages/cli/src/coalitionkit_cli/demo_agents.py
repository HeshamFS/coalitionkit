# SPDX-License-Identifier: Apache-2.0
"""Load the packaged neutral demonstration through the composition server."""

import importlib
from typing import Any

from coalitionkit_server.app import Server


def example_module(name: str) -> Any:
    modules = {
        "members.demo_runner": "coalitionkit_server.demo.runner",
        "members.demo_gateway": "coalitionkit_server.demo.gateway",
        "members.hosted_member.brain": "coalitionkit_server.demo.hosted_brain",
    }
    return importlib.import_module(modules[name])


def demo_runner(server: Server, coalition: str, pace: float = 2) -> Any:
    return example_module("members.demo_runner").Demo(server, coalition, pace)


def demo_gateway(*, live: bool = False) -> Any:
    return example_module("members.demo_gateway").demo_gateway(live=live)
