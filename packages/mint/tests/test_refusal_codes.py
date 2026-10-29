# SPDX-License-Identifier: Apache-2.0
"""Attack judging and the templates share one registry of refusal codes."""

import ast
from pathlib import Path
from typing import Any, cast

import pytest
from mcp import Client
from mcp.shared.exceptions import MCPError

from coalitionkit_mint.prove import STEWARD_CASE_CODES, rejected
from coalitionkit_mint.refusal import LIFECYCLE_CODES, POLICY_CODES, Refusal

SOURCE = Path(__file__).parents[1] / "src" / "coalitionkit_mint"


def raised_codes() -> set[str]:
    codes: set[str] = set()
    for path in SOURCE.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "Refusal"
                and node.args
            ):
                argument = node.args[0]
                assert isinstance(argument, ast.Constant), f"non-literal refusal in {path.name}"
                codes.add(cast("str", argument.value))
    return codes


def test_every_raised_refusal_code_is_registered() -> None:
    codes = raised_codes()
    assert codes, "the scan found no refusals"
    assert codes <= POLICY_CODES | LIFECYCLE_CODES


def test_an_unregistered_refusal_code_is_a_programming_error() -> None:
    with pytest.raises(TypeError, match="unregistered refusal code"):
        Refusal("not a code")


class RefusingClient:
    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message

    async def call_tool(self, tool: str, arguments: dict[str, Any]) -> Any:
        raise MCPError(self.code, self.message)


@pytest.mark.parametrize("code", sorted(POLICY_CODES))
async def test_a_steward_case_refused_by_any_policy_code_passes(code: str) -> None:
    client = cast("Client", RefusingClient(-32001, code))
    assert await rejected(client, "hold_slot", {}, STEWARD_CASE_CODES)


@pytest.mark.parametrize("code", sorted(LIFECYCLE_CODES))
async def test_a_lifecycle_refusal_proves_nothing(code: str) -> None:
    client = cast("Client", RefusingClient(-32001, code))
    assert not await rejected(client, "hold_slot", {}, STEWARD_CASE_CODES)


@pytest.mark.parametrize("config", ["resource", "device"], indirect=True)
def test_only_a_plain_read_is_not_an_attack(config: dict[str, Any]) -> None:
    from coalitionkit_mint.prove import not_an_attack, read_tools
    from coalitionkit_mint.schema import DeviceConfig, ResourceConfig

    model = (DeviceConfig if config["template"] == "device" else ResourceConfig).model_validate(
        config
    )
    for tool in read_tools(model):
        assert not_an_attack(model, tool, {})
        assert not not_an_attack(model, tool, {"extra": 1})
    for tool in ("hold_slot", "confirm", "cancel", "write", "read_unknown_field"):
        assert not not_an_attack(model, tool, {})
