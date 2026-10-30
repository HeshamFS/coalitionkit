# SPDX-License-Identifier: Apache-2.0
from unittest.mock import patch

from coalitionkit_runtime import Acknowledgement, projector
from coalitionkit_runtime.projector import ViewerProjection
from coalitionkit_runtime.steward import ReviewContext, Verdict
from coalitionkit_runtime.store import Document

from .conftest import World, accepted


def test_projection_only_delivers_new_events_and_revokes_on_leave(world: World) -> None:
    view = ViewerProjection(world.observer.name)
    world.host.update_view(view)
    assert view.document == world.host.view(world.observer.name)
    event = accepted(world.alice.send("observe", {"source": "chat", "content": "update"}))
    with patch.object(projector, "delivery", wraps=projector.delivery) as deliver:
        ops = world.host.update_view(view)
        assert deliver.call_count == 1
    assert ops[0]["path"] == "/events/" + event.accepted["event_id"]
    assert view.document == world.host.view(world.observer.name)
    assert world.host.update_view(view) == []
    assert isinstance(world.observer.send("leave", {}), Acknowledgement)
    ops = world.host.update_view(view)
    assert ops[0]["op"] == "replace"
    assert view.document == world.host.view(world.observer.name)
    assert event.accepted["event_id"] not in view.document["events"]


def test_host_passes_context_from_the_current_transaction(world: World) -> None:
    contexts: list[ReviewContext] = []

    class Checker:
        def review(self, envelope: Document, *, context: ReviewContext) -> Verdict:
            contexts.append(context)
            return Verdict()

    world.host.steward = Checker()
    accepted(
        world.alice.send(
            "observe",
            {"source": "chat", "content": "update"},
            {"audience": "participants", "participants": [world.alice.name, world.bob.name]},
        )
    )
    assert contexts[-1].members == frozenset(world.host.state.members)
    assert contexts[-1].consented == contexts[-1].members
    assert contexts[-1].recipients == frozenset({world.alice.name, world.bob.name})
