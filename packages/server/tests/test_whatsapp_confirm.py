# SPDX-License-Identifier: Apache-2.0
"""The confirm handoff: a reply opens a code; the signed-in person redeems it for the consent
request. Nothing is signed here."""

import re
from pathlib import Path
from urllib.parse import unquote

import pytest
from message_support import MsgWorld, message_world
from wa_server_support import Linked, link

from coalitionkit_surfaces import ConsentRequest, open_requests

__all__ = ["message_world"]


def ticket_code(rig: Linked) -> str:
    rig.say("1", f"pick-{len(rig.fake.requests)}")
    outcome = rig.mount.outcomes[-1]
    assert outcome.kind == "confirm" and outcome.ticket is not None
    return outcome.ticket.code


def planned(world: MsgWorld, tmp_path: Path) -> Linked:
    world.propose(world.need("Task for p1"), ["p1"])
    rig = link(world, tmp_path)
    return rig


def decides(world: MsgWorld) -> list[str]:
    return [
        e["event_id"]
        for e in world.host.store.read(world.host.coalition_id)
        if e["type"] == "coalition.decide" and e["payload"]["subject"]["kind"] != "charter"
    ]


def test_the_link_in_the_message_points_at_the_web_confirm_route(
    message_world: MsgWorld, tmp_path: Path
) -> None:
    rig = planned(message_world, tmp_path)
    code = ticket_code(rig)
    assert f"http://127.0.0.1:8000/confirm/{code}" in rig.texts()[-1]


def test_the_signed_in_person_redeems_the_code_and_gets_the_consent_request(
    message_world: MsgWorld, tmp_path: Path
) -> None:
    rig = planned(message_world, tmp_path)
    code = ticket_code(rig)
    log_before = len(message_world.host.store.read(rig.coalition))
    response = rig.redeem("tok-p1", code)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["metadata"]["subject"]["kind"] == "plan"
    assert body["id"] == f"plan:{body['metadata']['subject']['id']}:1:p1"
    assert "decision" in body["message"]
    assert len(message_world.host.store.read(rig.coalition)) == log_before  # nothing signed
    assert decides(message_world) == []
    assert message_world.host.open_consents("p1")  # still waiting for the owner-signed decision


def test_the_wrong_person_cannot_redeem_and_does_not_burn_the_code(
    message_world: MsgWorld, tmp_path: Path
) -> None:
    rig = planned(message_world, tmp_path)
    code = ticket_code(rig)
    assert rig.redeem("tok-p2", code).status_code == 403
    assert rig.redeem("nobody", code).status_code == 401
    assert rig.client.post("/v1/confirm/redeem", json={"code": code}).status_code == 401
    assert rig.redeem("tok-p1", code).status_code == 200


def test_a_code_works_once(message_world: MsgWorld, tmp_path: Path) -> None:
    rig = planned(message_world, tmp_path)
    code = ticket_code(rig)
    assert rig.redeem("tok-p1", code).status_code == 200
    again = rig.redeem("tok-p1", code)
    assert again.status_code == 409 and again.json()["detail"] == "already_used"
    assert rig.redeem("tok-p1", "no-such-code").status_code == 404


def test_an_expired_code_is_refused(message_world: MsgWorld, tmp_path: Path) -> None:
    rig = planned(message_world, tmp_path)
    code = ticket_code(rig)
    rig.clock.now += rig.mount.gate_ttl + 1
    expired = rig.redeem("tok-p1", code)
    assert expired.status_code == 410 and expired.json()["detail"] == "expired"


def test_a_code_for_a_superseded_revision_is_refused(
    message_world: MsgWorld, tmp_path: Path
) -> None:
    world = message_world
    task = world.need("Task for p1")
    tension = world.tension(task)
    rig = link(world, tmp_path)
    code = ticket_code(rig)
    world.tension(task, tension)  # the same tension, now at revision 2
    stale = rig.redeem("tok-p1", code)
    assert stale.status_code == 409 and stale.json()["detail"] == "stale_subject"


@pytest.mark.parametrize("who", ["tok-p1", "tok-p2"])
def test_redeem_needs_a_code_in_the_body(who: str, message_world: MsgWorld, tmp_path: Path) -> None:
    rig = planned(message_world, tmp_path)
    response = rig.client.post(
        "/v1/confirm/redeem", json={}, headers={"Authorization": f"Bearer {who}"}
    )
    assert response.status_code == 422


def test_following_the_message_link_reaches_the_request_the_trusted_flow_lists(
    message_world: MsgWorld, tmp_path: Path
) -> None:
    rig = planned(message_world, tmp_path)
    ticket_code(rig)  # a reply "1" opens the confirm step
    link = re.search(r"http://127\.0\.0\.1:8000(/confirm/\S+?)(?: or |\.? )", rig.texts()[-1])
    assert link is not None, rig.texts()[-1]
    path_code = unquote(link.group(1).removeprefix("/confirm/"))
    body = rig.redeem("tok-p1", path_code).json()  # what the web route does after sign-in
    request = ConsentRequest.parse(body["id"])
    assert request in open_requests(message_world.host, "p1")  # the existing signing flow's list
    assert request.decider == "p1"
