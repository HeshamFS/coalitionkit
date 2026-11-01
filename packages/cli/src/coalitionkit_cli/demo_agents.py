# SPDX-License-Identifier: Apache-2.0
"""Load the repository demonstration without adding example dependencies to the CLI."""

import importlib
import sys
from pathlib import Path
from typing import Any

from coalitionkit_server.app import Server


def example_module(name: str) -> Any:
    examples = Path(__file__).resolve().parents[4] / "examples"
    if not examples.is_dir():
        raise ValueError("demo member examples require a repository checkout")
    if str(examples) not in sys.path:
        sys.path.insert(0, str(examples))
    return importlib.import_module(name)


def demo_runner(server: Server, coalition: str, pace: float = 2) -> Any:
    return example_module("members.demo_runner").Demo(server, coalition, pace)


def demo_gateway(*, live: bool = False) -> Any:
    return example_module("members.demo_gateway").demo_gateway(live=live)
