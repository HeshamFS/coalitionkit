# SPDX-License-Identifier: Apache-2.0
"""The setup sender is the responder; only the requester may request count."""

from __future__ import annotations

import pytest

from .conftest import World, accepted, error


@pytest.mark.parametrize("trusted_requester", [False, True])
def test_count_setup_authorizes_requester(world: World, trusted_requester: bool) -> None:
    charter = {
        **world.host.state.charter,
        "count_trusted": [world.bob.name if trusted_requester else world.alice.name],
    }
    accepted(world.host.host_emit("charter", charter, {"audience": "coalition"}))
    task = world.need().accepted["payload"]["need_id"]
    world.query(task)
    body = {
        "match_id": "m1",
        "task_id": task,
        "peer": world.bob.name,
        "round": "setup",
        "blob": "",
        "reveal": "count",
    }
    reply = world.alice.send("match", body)
    if not trusted_requester:
        error(reply, "not_authorized")
        return
    accepted(reply)
    accepted(world.bob.send("match", {**body, "peer": world.alice.name, "round": "request"}))
    accepted(world.alice.send("match", {**body, "round": "response"}))
    assert world.host.state.matches["m1"]["requester"] == world.bob.name
    assert world.host.state.matches["m1"]["round"] == "response"
