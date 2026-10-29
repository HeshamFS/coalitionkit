# SPDX-License-Identifier: Apache-2.0
"""Fail closed on imports and dynamic execution in reviewed template modules."""

import ast
from pathlib import Path

ALLOWED = {
    "uuid",
    "sqlite3",
    "time",
    "typing",
    "coalitionkit_mint.schema",
    "coalitionkit_mint.refusal",
}
FORBIDDEN_CALLS = {"eval", "exec", "compile", "__import__", "getattr", "globals", "locals"}


def scan_templates(folder: Path) -> None:
    for path in folder.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or ""]
                if node.level:
                    raise ValueError("relative template import is not reviewed")
            if any(module not in ALLOWED for module in modules):
                raise ValueError("unreviewed template import: " + path.name)
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in FORBIDDEN_CALLS
            ):
                raise ValueError("dynamic template execution")
