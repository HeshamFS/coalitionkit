# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false, reportOptionalMemberAccess=false, reportOptionalIterable=false
"""Writes need a person: elicitation, owner-signed consent, and forged flags."""

from __future__ import annotations

from typing import Any

import pytest
from mcp_types import InputRequiredResult

from coalitionkit_contracts import verify_consent, verify_decision
from coalitionkit_mcp.testing_rig import C1, COMMITMENT, PLAN, Rig, no, yes


def never(_: Any) -> Any:
    raise AssertionError("the person must not be asked by this client")


SUBJECT = {"kind": "plan", "id": PLAN, "revision": 1}
DECIDE = {"coalition_id": C1, "subject": SUBJECT, "choice": PLAN}


def verified(rig: Rig, participant: str, envelope: dict[str, Any]) -> None:
    person = rig.people[participant]
    verify_decision(envelope, person.agent_key.public_key(), person.owner_key.public_key())


async def test_decide_without_the_persons_answer_never_reaches_the_host(rig: Rig) -> None:
    async with rig.connect("p1", never) as client:
        first = await client.session.call_tool("decide", DECIDE, allow_input_required=True)
    assert isinstance(first, InputRequiredResult)
    asked = next(iter(first.input_requests.values()))
    message = str(asked.params.message)  # type: ignore[union-attr]
    assert PLAN in message and "revision 1" in message
    assert rig.host.calls == []


@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        ("decide", {**DECIDE, "consent": True, "confirmed": True}),
        ("accept_charter", {"coalition_id": C1}),
        ("approve_commitment", {"coalition_id": C1, "commitment_id": COMMITMENT}),
    ],
)
async def test_a_client_that_cannot_ask_is_told_where_the_person_signs(
    rig: Rig, tool: str, arguments: dict[str, Any]
) -> None:
    async with rig.connect("p1") as client:
        result = await client.call_tool(tool, arguments)
    assert result.is_error
    text = result.content[0].text
    assert "nothing was signed" in text and "/signin" in text
    # The agent learns where its person goes, never a token or a link it could sign through.
    assert "token=" not in text and "http" not in text
    assert result.structured_content["code"] == "not_authorized"
    assert rig.host.calls == []


async def test_decide_with_the_answer_signs_consent_with_the_owner_key(rig: Rig) -> None:
    async with rig.connect("p1", yes) as client:
        result = await client.call_tool("decide", DECIDE)
    assert not result.is_error, result
    sent = rig.host.accepted[-1]
    assert sent["type"] == "coalition.decide" and sent["on_behalf_of"] == "p1"
    assert sent["payload"]["consent"] is True and sent["payload"]["subject"] == SUBJECT
    verified(rig, "p1", sent)
    assert "revision 1" in rig.asked[0]


async def test_a_forged_consent_flag_is_ignored(rig: Rig) -> None:
    forged = {**DECIDE, "consent": True, "confirm": True, "confirmed": True, "approved": True}
    async with rig.connect("p1", no) as client:
        result = await client.call_tool("decide", forged)
    assert not result.is_error
    assert rig.host.accepted[-1]["payload"]["consent"] is False  # the person said no
    verified(rig, "p1", rig.host.accepted[-1])
    # And the opposite: the argument says no, the person says yes.
    async with rig.connect("p1", yes) as client:
        await client.call_tool("decide", {**DECIDE, "consent": False})
    assert rig.host.accepted[-1]["payload"]["consent"] is True


async def test_a_declined_question_signs_nothing(rig: Rig) -> None:
    def decline(_: Any) -> Any:
        from mcp_types import ElicitResult

        return ElicitResult(action="decline")

    async with rig.connect("p1", decline) as client:
        result = await client.call_tool("decide", DECIDE)
    assert result.is_error and (result.structured_content or {})["code"] == "not_authorized"
    assert rig.host.calls == []


async def test_the_consent_only_verifies_for_its_own_participant(rig: Rig) -> None:
    async with rig.connect("p1", yes) as client:
        await client.call_tool("decide", DECIDE)
    sent = rig.host.accepted[-1]
    other = rig.people["p2"].owner_key.public_key()
    own = rig.people["p1"].owner_key.public_key()
    verify_consent(C1, sent["payload"], own, participant="p1")
    try:
        verify_consent(C1, sent["payload"], other, participant="p1")
    except Exception as exc:
        assert "verify" in str(exc)
    else:
        raise AssertionError("consent verified under another participant's key")


async def test_approve_commitment_signs_the_current_revision(rig: Rig) -> None:
    async with rig.connect("p1", yes) as client:
        result = await client.call_tool(
            "approve_commitment", {"coalition_id": C1, "commitment_id": COMMITMENT}
        )
    assert not result.is_error, result
    sent = rig.host.accepted[-1]
    assert sent["payload"]["subject"] == {"kind": "commitment", "id": COMMITMENT, "revision": 3}
    assert "revision 3" in rig.asked[0]
    verified(rig, "p1", sent)


async def test_approve_commitment_without_an_answer_sends_nothing(rig: Rig) -> None:
    args = {"coalition_id": C1, "commitment_id": COMMITMENT, "confirmed": True}
    async with rig.connect("p1", never) as client:
        first = await client.session.call_tool(
            "approve_commitment", args, allow_input_required=True
        )
    assert isinstance(first, InputRequiredResult)
    assert rig.host.calls == []


async def test_accept_charter_signs_the_current_revision(rig: Rig) -> None:
    async with rig.connect("p2", yes) as client:
        result = await client.call_tool("accept_charter", {"coalition_id": C1})
    assert not result.is_error, result
    sent = rig.host.accepted[-1]
    assert sent["payload"]["subject"] == {"kind": "charter", "id": C1, "revision": 2}
    assert sent["payload"]["choice"] == C1
    verified(rig, "p2", sent)


async def test_consent_tools_refuse_a_foreign_coalition_before_asking(rig: Rig) -> None:
    from coalitionkit_mcp.testing_rig import C2

    async with rig.connect("p2", yes) as client:
        result = await client.call_tool("accept_charter", {"coalition_id": C2})
    assert result.is_error and (result.structured_content or {})["code"] == "unknown_participant"
    assert rig.asked == [] and rig.host.calls == []


async def test_a_revision_change_asks_again_instead_of_reusing_the_answer(rig: Rig) -> None:
    async with rig.connect("p2", never) as client:
        first = await client.session.call_tool(
            "accept_charter", {"coalition_id": C1}, allow_input_required=True
        )
        assert isinstance(first, InputRequiredResult)
        answers = {
            key: {"action": "accept", "content": {"consent": True}} for key in first.input_requests
        }
        rig.view.by_id[C1].revisions[("charter", C1)] = 5  # the charter changed meanwhile
        again = await client.session.call_tool(
            "accept_charter",
            {"coalition_id": C1},
            input_responses=answers,  # type: ignore[arg-type]
            request_state=first.request_state,
            allow_input_required=True,
        )
    assert isinstance(again, InputRequiredResult)
    assert "revision 5" in str(next(iter(again.input_requests.values())).params.message)  # type: ignore[union-attr]
    assert rig.host.calls == []
