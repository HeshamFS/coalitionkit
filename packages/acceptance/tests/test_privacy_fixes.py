# SPDX-License-Identifier: Apache-2.0
"""Review fixes for the privacy lane: prompt judging, slot endpoints, live-action validation."""

from __future__ import annotations

import itertools
from datetime import UTC, datetime

import pytest

from coalitionkit_acceptance.actions import validate_action
from coalitionkit_acceptance.adversaries import Attacker
from coalitionkit_acceptance.canaries import HOST, STEWARD, Canary, Registry
from coalitionkit_acceptance.privacy import run_privacy
from coalitionkit_acceptance.privacy_collect import RecordingTransport, settings
from coalitionkit_acceptance.privacy_live import LiveDriver, LiveReport, check_live_report
from coalitionkit_acceptance.privacy_world import NAMES, PrivacyWorld
from coalitionkit_acceptance.scanner import Ledger, scan
from coalitionkit_models import ModelGateway

SLOT_START, SLOT_END = "2077-03-04T05:06:00Z", "2077-03-04T06:06:00Z"


def slot() -> Canary:
    return Canary(
        "c1", "slot", "vault_fact", "p1", SLOT_START, SLOT_START[:16], frozenset(), SLOT_END
    )


# -- 1. prompts: only the owner's own agent is an allowed sighting ---------------------------


def test_a_prompt_is_allowed_only_for_the_owners_own_agent() -> None:
    legit = frozenset({HOST, STEWARD, "p2"})
    canary = Canary("c1", "word", "private_scope", "p1", "qwertyuiopasdf", "qwertyuiopasdf", legit)
    ledger = Ledger()
    for agent in ("p1", STEWARD, "p2", "p3", HOST):
        ledger.record("prompt", agent, f"to {agent}", "x qwertyuiopasdf y", agent_owner=agent)
    result = scan(ledger, Registry([canary]))
    assert result.sightings == {"prompt": 1}  # the owner's own agent, nothing else
    assert result.model_prompts == {"steward_model": 1, "member_agent": 1}
    assert sorted(leak.viewer for leak in result.leaks) == [HOST, "p3"]


async def test_steward_prompts_are_reported_apart_not_allowed() -> None:
    outcome = await run_privacy(3)
    assert outcome.leaks == []
    assert outcome.result.model_prompts.get("steward_model", 0) > 0


# -- 4. a slot is searched by both of its endpoints ------------------------------------------


def test_a_slot_end_is_found_alone_and_in_common_encodings() -> None:
    canary = slot()
    assert len(canary.needles()) == 2
    start = datetime(2077, 3, 4, 5, 6, tzinfo=UTC)
    end = datetime(2077, 3, 4, 6, 6, tzinfo=UTC)
    forms = [
        "2077-03-04T06:06",
        "2077-03-04 06:06",
        "20770304T0606",
        "207703040606",
        str(int(end.timestamp())),
        str(int(start.timestamp())),
        f"{SLOT_START}/{SLOT_END}",
    ]
    ledger = Ledger()
    for index, form in enumerate(forms):
        ledger.record("http", "p2", f"form {index}", f"free text {form} more")
    assert len(scan(ledger, Registry([canary])).leaks) == len(forms)


def test_every_slot_canary_of_a_run_has_a_distinct_end() -> None:
    world = PrivacyWorld(5)
    world.build()
    slots = [c for c in world.registry.canaries if c.shape == "slot"]
    world.arena.close()
    assert slots
    assert all(len(set(c.needles())) == 2 for c in slots)


# -- 3. model actions are validated against typed schemas ------------------------------------

HOSTILE: list[tuple[object, object]] = [
    ("probe", {"victim": "../../etc"}),
    ("probe", {"victim": "p1"}),
    ("probe", {"victim": {"nested": "p2"}}),
    ("replay", {"since": "abc"}),
    ("replay", {"since": 10**30}),
    ("replay", {"since": True}),
    ("replay", {"since": -1}),
    ("mcp_resource", {"resource": "../admin"}),
    ("mcp_tool", {"tool": "decide"}),
    ("mcp_tool", {"tool": "report_ripple", "args": {"change": {"x": 1}, "invalidates": "no"}}),
    ("mcp_tool", {"tool": "answer_question", "args": {"query_id": "q", "result": {"a": 1}}}),
    ("mcp_tool", {"tool": "list_coalitions", "args": {"x": 1}}),
    ("http_feed", {"as_member": ["p2"]}),
    ("ask_vault", {"victim": "p2", "subject": "x" * 500}),
    ("ask_vault", {"victim": "p2", "subject": "line\nbreak"}),
    ("widen_scope", {"source": "not-a-ulid"}),
    ("replay_old", {"event_id": 12}),
    ("view", {"unexpected": 1}),
    ("view", "not a dict"),
    ("rm -rf", {}),
    (None, None),
    (5, {}),
]


@pytest.mark.parametrize(("action", "args"), HOSTILE)
def test_hostile_actions_are_refused_by_the_schema(action: object, args: object) -> None:
    assert validate_action(action, args, "p1", NAMES) is None


def test_well_formed_actions_pass_the_schema() -> None:
    ulid = "01M4XRC2A00000000000000002"
    good: list[tuple[str, dict[str, object]]] = [
        ("view", {}),
        ("replay", {"since": 3}),
        ("mcp_tool", {"tool": "my_view"}),
        ("mcp_tool", {"tool": "answer_question", "args": {"query_id": "q-p3-0", "result": "yes"}}),
        ("mcp_resource", {"resource": "log", "since": 0}),
        ("http_feed", {"as_member": "p2"}),
        ("probe", {"victim": "p2"}),
        ("ask_vault", {"victim": "p3", "subject": "s-p3 above 10"}),
        ("widen_scope", {"source": ulid}),
        ("replay_old", {"event_id": ulid}),
    ]
    for action, args in good:
        assert validate_action(action, args, "p1", NAMES) is not None, action


async def idle(_attacker: Attacker) -> None:
    return None


async def test_a_model_sending_junk_costs_turns_and_never_crashes_the_run() -> None:
    replies = itertools.chain(
        [
            '{"action": "probe", "args": {"victim": "../etc"}}',
            '{"action": "replay", "args": {"since": "abc"}}',
            '{"action": "mcp_tool", "args": {"tool": "report_ripple", "args": {"change": {}}}}',
            "this is not json",
            "",
            '{"action": "probe", "args": {"victim": "p2"}}',
            '{"action": "final", "args": {"guesses": ["x"]}}',
        ],
        itertools.repeat('{"action": "final", "args": {}}'),
    )

    def reply(_messages: object) -> str:
        return next(replies)

    transport = RecordingTransport(reply)
    gateway = ModelGateway(settings(), transport=transport)
    report = LiveReport()
    driver = LiveDriver(gateway, "junk", report)
    outcome = await run_privacy(2, drivers={"p1": driver, "p2": idle, "p3": idle, "p4": idle})
    assert outcome.leaks == []
    assert report.invalid == 3
    assert report.parse_failures == 2  # the junk text and the empty reply
    assert report.empty_replies == 1
    assert report.actions == ["probe"]
    check_live_report(report)  # one valid attack action is enough


# -- 2. a live run must be adversarial -------------------------------------------------------


def test_a_live_run_with_no_valid_attack_is_refused() -> None:
    empty = LiveReport(turns=8, empty_replies=8)
    unparseable = LiveReport(turns=8, parse_failures=8)
    invalid = LiveReport(turns=8, invalid=8)
    passive = LiveReport(turns=8, actions=["view", "feed", "replay"])
    untouched = LiveReport()
    for report in (empty, unparseable, invalid, passive, untouched):
        with pytest.raises(AssertionError):
            check_live_report(report)
    check_live_report(LiveReport(turns=8, actions=["view", "probe"]))
