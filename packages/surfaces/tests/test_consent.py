# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

import pytest
from ag_ui.core import (
    Interrupt,
    RunFinishedEvent,
    RunFinishedInterruptOutcome,
    RunFinishedSuccessOutcome,
    RunStartedEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
)
from surfaces_support import World, dump

from coalitionkit_contracts import jwk_to_public_key, verify_decision
from coalitionkit_surfaces import AgentSession, ConsentError, SurfaceHub, open_requests
from coalitionkit_surfaces.fakes import FakeClock
from coalitionkit_surfaces.frames import Frame


def agent(hub: SurfaceHub, viewer: str) -> AgentSession:
    return hub.agent_session(viewer)


def plan_for_alice_and_bob(world: World) -> str:
    return world.propose(world.need(), ["alice"])


def interrupts(frames: Sequence[Frame]) -> list[Interrupt]:
    finished = next(f for f in frames if isinstance(f, RunFinishedEvent))
    assert isinstance(finished.outcome, RunFinishedInterruptOutcome)
    return finished.outcome.interrupts


def test_open_requests_are_shown_as_interrupts_to_deciders_only(
    world: World, hub: SurfaceHub
) -> None:
    plan = plan_for_alice_and_bob(world)
    shown = interrupts(agent(hub, "alice").start())
    assert {i.id for i in shown} == {f"plan:{plan}:1:alice"}
    assert shown[0].reason == "consent_required"
    assert shown[0].metadata == {"subject": {"kind": "plan", "id": plan, "revision": 1}}
    carol = agent(hub, "carol").start()
    assert [type(f) for f in carol] == [RunStartedEvent, RunFinishedEvent]
    assert isinstance(carol[1], RunFinishedEvent)
    assert isinstance(carol[1].outcome, RunFinishedSuccessOutcome)


def test_agent_text_streams_as_text_message_events(world: World, hub: SurfaceHub) -> None:
    session = agent(hub, "alice")
    session.say("Hello")
    frames = session.start()
    kinds = [type(f) for f in frames]
    assert kinds[1:4] == [TextMessageStartEvent, TextMessageContentEvent, TextMessageEndEvent]
    assert "Hello" in dump(frames)
    other = agent(hub, "bob").start()
    assert "Hello" not in dump(other)


def test_answer_is_an_owner_signed_decide_the_host_accepts(world: World, hub: SurfaceHub) -> None:
    plan = plan_for_alice_and_bob(world)
    result = agent(hub, "alice").answer(f"plan:{plan}:1:alice", True)
    assert result["status"] == "accepted"
    assert isinstance(result["consent_sig"], str) and result["consent_sig"].count(".") == 2
    decide = world.host.store.read(world.host.coalition_id)[-1]
    assert decide["type"] == "coalition.decide" and decide["on_behalf_of"] == "alice"
    jwk = world.host.state.members["alice"]["owner_key"]
    verify_decision(decide, world.alice.agent.public_key(), jwk_to_public_key(jwk))
    assert open_requests(world.host, "alice") == []


def test_c18_answer_for_another_viewers_request_is_refused(world: World, hub: SurfaceHub) -> None:
    plan = plan_for_alice_and_bob(world)
    before = len(world.host.store.read(world.host.coalition_id))
    with pytest.raises(ConsentError) as caught:
        agent(hub, "bob").answer(f"plan:{plan}:1:alice", True)
    assert caught.value.code == "not_your_request"
    assert len(world.host.store.read(world.host.coalition_id)) == before
    assert len(open_requests(world.host, "alice")) == 1


def test_c18_one_answer_per_decider_per_revision(world: World, hub: SurfaceHub) -> None:
    plan = plan_for_alice_and_bob(world)
    session = agent(hub, "alice")
    session.answer(f"plan:{plan}:1:alice", True)
    with pytest.raises(ConsentError) as caught:
        session.answer(f"plan:{plan}:1:alice", False)
    assert caught.value.code == "not_open"
    decides = [e for e in world.host.store.read(world.host.coalition_id) if "decide" in e["type"]]
    assert sum(1 for e in decides if e["payload"]["subject"]["id"] == plan) == 1


def test_c18_stale_revision_request_is_not_answerable(world: World, hub: SurfaceHub) -> None:
    plan = plan_for_alice_and_bob(world)
    with pytest.raises(ConsentError) as caught:
        agent(hub, "alice").answer(f"plan:{plan}:2:alice", True)
    assert caught.value.code == "not_open"


def test_c18_decision_not_signed_by_the_owner_key_is_never_sent(
    world: World, hub: SurfaceHub
) -> None:
    plan = plan_for_alice_and_bob(world)
    signer = world.alice.signer
    signer.sign_consent_with_agent_key = True
    session = AgentSession(world.host, "alice", signer, clock=FakeClock())
    before = len(world.host.store.read(world.host.coalition_id))
    with pytest.raises(ConsentError) as caught:
        session.answer(f"plan:{plan}:1:alice", True)
    assert caught.value.code == "bad_signature"
    assert len(world.host.store.read(world.host.coalition_id)) == before


def test_c18_signer_answering_differently_than_the_person_is_refused(
    world: World, hub: SurfaceHub
) -> None:
    plan = plan_for_alice_and_bob(world)

    class Flipping:
        def sign_decision(
            self, subject: dict[str, Any], choice: str, consent: bool
        ) -> dict[str, Any]:
            return world.alice.signer.sign_decision(subject, choice, not consent)

    session = AgentSession(world.host, "alice", Flipping(), clock=FakeClock())
    with pytest.raises(ConsentError) as caught:
        session.answer(f"plan:{plan}:1:alice", True)
    assert caught.value.code == "signer_mismatch"


def test_choice_must_equal_the_subject_id(world: World, hub: SurfaceHub) -> None:
    plan = plan_for_alice_and_bob(world)
    with pytest.raises(ConsentError) as caught:
        agent(hub, "alice").answer(f"plan:{plan}:1:alice", True, "other")
    assert caught.value.code == "bad_choice"


def test_an_answer_resumes_with_a_new_run_covering_the_open_interrupts(
    world: World, hub: SurfaceHub
) -> None:
    plan = plan_for_alice_and_bob(world)
    session = agent(hub, "alice")
    session.start()
    assert session.changed() == []
    session.answer(f"plan:{plan}:1:alice", True)
    frames = session.changed()
    finished = next(f for f in frames if isinstance(f, RunFinishedEvent))
    assert isinstance(finished.outcome, RunFinishedSuccessOutcome)


def test_interrupt_ids_roundtrip_json(world: World, hub: SurfaceHub) -> None:
    plan_for_alice_and_bob(world)
    shown = interrupts(agent(hub, "alice").start())
    assert json.loads(shown[0].model_dump_json())["id"].startswith("plan:")
