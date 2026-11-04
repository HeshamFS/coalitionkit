# SPDX-License-Identifier: Apache-2.0
"""The per-room spending cap: past ``room_budget_usd`` a room's model calls are refused.

The gateway's meter already records what each call cost, per room. Before a room asks a model
(a hosted agent's question, an offer, a made thing, a picture), it checks the meter against the
cap. Past it, the call is not sent, the caller falls back to its rules, and the Table says so
once. A host without a cap, or without a meter, never refuses.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .engine import RoomEngine

WHY = "This room has used its model budget, so the rules answer from here."


def cap(engine: RoomEngine) -> float | None:
    return engine.server.settings.room_budget_usd


def spent_usd(engine: RoomEngine, coalition: str) -> float:
    meter = engine.server.gateway.meter
    return meter.total(coalition) / 1_000_000 if meter is not None else 0.0


def reached(engine: RoomEngine, coalition: str) -> bool:
    """True when the room may not call a model any more. Says so on the Table the first time."""
    most = cap(engine)
    if most is None or spent_usd(engine, coalition) < most:
        return False
    if not engine.read(coalition).get("budget_reached"):
        engine.update(coalition, lambda d: d.__setitem__("budget_reached", True))
        engine.note(
            coalition,
            "stopped",
            f"Model budget reached (${most:.2f} for this room): no more model calls; "
            "the rules answer from here.",
        )
    return True
