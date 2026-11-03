# SPDX-License-Identifier: Apache-2.0
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportMissingParameterType=false, reportPrivateUsage=false
"""A message the Steward holds is shown, never retried with the same words, and never wedges."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from room_flow import briefs_open, full_room, reply_brief
from room_rig import BRIEF, NEEDS, RoomModel, engine_of, events, serve, until, view_of

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
