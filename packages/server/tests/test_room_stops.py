# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportMissingParameterType=false, reportPrivateUsage=false
"""A message the Steward holds is shown, never retried with the same words, and never wedges."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from room_flow import briefs_open, full_room, reply_brief
from room_rig import (
    BRIEF,
    NEEDS,
    RoomModel,
    engine_of,
    events,
    serve,
    server_of,
    until,
    view_of,
)

from coalitionkit_runtime.steward import FakeSteward, ReviewContext, Verdict


class Holding(FakeSteward):
    """Holds the kinds of event named, for the senders named, and counts every review."""

    def __init__(self, kinds: set[str], senders: set[str] | None, policy: str) -> None:
        super().__init__(Verdict())
        self.kinds, self.senders, self.policy = kinds, senders, policy
        self.held: list[str] = []

    def review(self, envelope: dict[str, Any], *, context: ReviewContext) -> Verdict:
        if envelope["type"] in self.kinds and (
            self.senders is None or envelope["on_behalf_of"] in self.senders
        ):
            self.held.append(envelope["type"])
            return Verdict("escalate", self.policy)
        return super().review(envelope, context=context)


def test_a_held_offer_is_shown_and_the_room_moves_on(tmp_path: Path) -> None:
    steward = Holding({"coalition.offer"}, {"p2"}, "no-regulated-advice")
    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF)) as client:
        room, (a, b) = full_room(client, steward=steward)
        cid, engine = room["coalition_id"], engine_of(client)
        briefs_open(engine, cid, ["p1", a["participant"], b["participant"]])
        for who in (room["owner"], a, b):
            reply_brief(client, who["token"], {"q1": None, "q2": 2, "q3": None})
        until(lambda: engine.read(cid)["offers_done"], 40, "offers to finish despite the hold")
        stops = view_of(engine, cid, "p1")["stops"]
        assert stops and {s["seat"] for s in stops} == {"p2"}
        assert all(s["policy"] == "no-regulated-advice" and s["explain"] for s in stops)
        assert all(s["to"] is None for s in stops)
        assert [e for e in events(client, cid, "offer") if e["on_behalf_of"] == "p2"] == []
        said = [x for x in view_of(engine, cid, "p1")["activity"] if x["verb"] == "stopped"]
        assert said and "Steward held" in said[0]["label"]
        until(lambda: engine.may_plan(cid), 40, "the room to move on")


def test_a_held_plan_set_is_not_sent_again_until_the_offers_change(tmp_path: Path) -> None:
    steward = Holding({"coalition.propose"}, None, "fairness-cap-exceeded")
    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF)) as client:
        room, (a, b) = full_room(client, steward=steward)
        cid, engine = room["coalition_id"], engine_of(client)
        briefs_open(engine, cid, ["p1", a["participant"], b["participant"]])
        for who in (room["owner"], a, b):
            reply_brief(client, who["token"], {"q1": None, "q2": 2, "q3": None})
        until(lambda: steward.held, 60, "the Steward to hold the plans")
        time.sleep(4)
        assert len(steward.held) <= 2, f"the held set was sent {len(steward.held)} times"
        assert not events(client, cid, "propose")
        stops = view_of(engine, cid, "p1")["stops"]
        assert [s["policy"] for s in stops] == ["fairness-cap-exceeded"]
        assert "60" in stops[0]["explain"]


def real_steward_room(client: Any, watch: bool = False) -> tuple[str, Any, Any]:
    """A silent three-seat room under the real Steward, with every offer posted by hand."""
    from room_rig import bearer, join, sign, start_room
    from test_room_choices import OFFERS

    room = start_room(client, seats=3, real_steward=True)
    cid, engine = room["coalition_id"], engine_of(client)
    steward = server_of(client).steward
    until(lambda: steward._ready is not None and steward._ready.done(), 30, "the Steward")  # pyright: ignore[reportPrivateUsage]
    a, b = join(client, room), join(client, room)
    people = {"p1": room["owner"], a["participant"]: a, b["participant"]: b}
    for who, person in people.items():
        sign(client, cid, person["token"], who)
    until(lambda: len(events(client, cid, "need")) >= 3, 30, "needs")
    briefs_open(engine, cid, list(people))
    for person in people.values():
        reply_brief(client, person["token"], {"q1": None, "q2": 0, "q3": None})
    until(lambda: engine.may_plan(cid), 40, "ready for plans")
    needs = [e["payload"]["need_id"] for e in events(client, cid, "need")]
    engine.update(cid, lambda d: d.__setitem__("change_pending", True))
    for who, rows in zip(people, OFFERS.values(), strict=True):
        for need, (minutes, effort) in zip(needs, rows, strict=True):
            cost = {"minutes": minutes, "money": 0, "effort": effort}
            client.post(
                "/v1/agent/offer",
                json={"need_id": need, "cost": cost},
                headers=bearer(people[who]["token"]),
            )
    session = None
    if watch:  # a screen that is already open when the audit starts
        session = server_of(client).surfaces[cid].state.hub.feed_session("p1")
        session.start()
    engine.update(cid, lambda d: d.__setitem__("change_pending", False))
    engine.wake_gardener(cid)
    return cid, engine, session


LABEL = "The Steward is checking the plans"


def test_the_steward_checking_the_plans_is_shown_while_it_runs_and_when_it_ends(
    tmp_path: Path,
) -> None:
    scripted = RoomModel(needs=NEEDS, brief=BRIEF, steward_delay=3.0)
    with serve(tmp_path, scripted) as client:
        cid, engine, session = real_steward_room(client, watch=True)
        hub = server_of(client).surfaces[cid].state.hub
        seen: list[str] = []

        def running() -> bool:
            lines = view_of(engine, cid, "p1")["activity"]
            seen.extend(x["state"] for x in lines if x["label"] == LABEL)
            return "running" in seen

        until(running, 40, "the audit to show as running")
        # The open screen is told at once, without waiting for the host's lock to come free.
        from ag_ui.core import StateDeltaEvent

        from coalitionkit_runtime import Subscription

        started = time.monotonic()
        frames = hub._poll(session, Subscription(cid, 0))  # pyright: ignore[reportPrivateUsage]
        assert time.monotonic() - started < 1.0, "the poll waited for the host"
        told = [op for f in frames if isinstance(f, StateDeltaEvent) for op in f.delta]
        assert any("running" in str(getattr(op, "value", "")) for op in told), told
        until(lambda: events(client, cid, "propose"), 40, "the plans after the audit")
        until(
            lambda: any(
                x["label"] == LABEL and x["state"] == "done"
                for x in view_of(engine, cid, "p1")["activity"]
            ),
            20,
            "done",
        )
        line = next(x for x in view_of(engine, cid, "p1")["activity"] if x["label"] == LABEL)
        assert line["ms"] >= 2500 and line["source"] == "host"


def test_an_outage_of_the_steward_is_a_visible_hold(tmp_path: Path) -> None:
    """The real Steward with no model reachable fails closed: the audit cannot run, the plan
    set is held, and the room shows the checking and the hold."""
    with serve(tmp_path, RoomModel(needs=NEEDS, brief=BRIEF)) as client:
        cid, engine, _ = real_steward_room(client)
        until(lambda: engine.read(cid)["stops"], 40, "the hold")
        finished = lambda: [  # noqa: E731
            x
            for x in view_of(engine, cid, "p1")["activity"]
            if x["label"] == LABEL and x["state"] != "running"
        ]
        checking = until(finished, 20, "the audit to be written down")
        assert checking[0]["state"] == "failed" and checking[0]["ms"] is not None
        stops = view_of(engine, cid, "p1")["stops"]
        assert stops[0]["policy"] == "steward-model-audit" and stops[0]["seat"] is None
        assert not events(client, cid, "propose"), "failing closed: no plan without the audit"
