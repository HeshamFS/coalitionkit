# SPDX-License-Identifier: Apache-2.0
"""A no on a plan does not freeze the room: new plans come, and never the one turned down."""

from pathlib import Path
from typing import Any

from room_rig import bearer, engine_of, events, serve, server_of, until
from test_room_choices import OFFERS, make_offers, silent_room
from test_room_work import model

KINDS = {"plan", "tension_option"}


def signature(assignments: list[dict[str, Any]]) -> frozenset[tuple[str, str]]:
    return frozenset((str(a["task_id"]), str(a["assignee"])) for a in assignments)


def refuse_first_ask(client: Any, cid: str, people: dict[str, Any], who: str) -> dict[str, Any]:
    host = server_of(client).hosts[cid]
    ask = next(a for a in host.open_consents(who) if a["kind"] in KINDS)
    body: dict[str, Any] = {
        "interrupt_id": f"{ask['kind']}:{ask['id']}:{ask['revision']}:{who}",
        "consent": False,
    }
    if ask["kind"] == "tension_option":
        tension = next(
            e for e in events(client, cid, "tension") if e["payload"]["tension_id"] == ask["id"]
        )
        body["choice"] = tension["payload"]["options"][0]["option_id"]
    reply = client.post("/v1/agent/answers", json=body, headers=bearer(people[who]["token"]))
    assert reply.status_code == 200, reply.text
    return ask


def test_a_no_brings_new_plans_or_says_there_are_none(tmp_path: Path) -> None:
    with serve(tmp_path, model()) as client:
        cid, engine, people = silent_room(client)
        make_offers(client, cid, dict(zip(OFFERS, people.values(), strict=True)))
        until(lambda: events(client, cid, "propose"), 40, "plans")
        host = server_of(client).hosts[cid]
        who = next(iter(people))
        until(
            lambda: any(a["kind"] in KINDS for a in host.open_consents(who)),
            20,
            "something to decide",
        )
        turned_down: set[frozenset[tuple[str, str]]] = set()
        for _ in range(12):
            before = len(events(client, cid, "propose"))
            ask = refuse_first_ask(client, cid, people, who)
            if ask["kind"] == "plan":
                turned_down.add(signature(host.state.subject("plan", ask["id"])["assignments"]))

            def moved(before: int = before) -> bool:
                if engine.read(cid)["stops"]:
                    return True
                fresh = events(client, cid, "propose")[before:]
                return bool(fresh) and any(a["kind"] in KINDS for a in host.open_consents(who))

            until(moved, 30, "new plans or a plain stop after a no")
            for event in events(client, cid, "propose")[before:]:
                for plan in event["payload"]["plans"]:
                    assert signature(plan["assignments"]) not in turned_down, (
                        "a refused plan came back"
                    )
            stops = engine_of(client).read(cid)["stops"]
            if stops:
                assert stops[-1]["policy"] == "plans-refused"
                assert "turned down" in stops[-1]["explain"]
                return
        raise AssertionError("the room kept proposing after every plan was turned down")
