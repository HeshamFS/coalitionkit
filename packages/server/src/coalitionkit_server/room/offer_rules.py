# SPDX-License-Identifier: Apache-2.0
"""What an offer means, and the pure rules around it.

An offer says: "I could do this, and it would take me about this long." Offers are alternatives,
not a bill. Each one carries that person's own estimate for that one need, capped by the most
time they said they would give to any one job; estimates are never summed against that cap. The
effort says how well the job fits: low for what they prefer, high for what they would rather not
do. Nothing here calls a model or touches the log, so the guarantees can be tested alone.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

from ..adapter import Document

Effort = Literal["low", "medium", "high"]
MIN_MINUTES = 5
MAX_MINUTES = 60 * 24 * 7
HELPER_MINUTES = 15
# A first guess at how long one job of each kind takes, before a person's own words adjust it.
BASE_MINUTES = {"place": 60, "schedule": 30, "budget": 45, "list": 30, "draft": 90}


class OfferItem(BaseModel):
    need_id: str
    minutes: int
    money: int
    effort: Effort


class OffersReply(BaseModel):
    offers: list[OfferItem]
    note: str


@dataclass(frozen=True)
class Limits:
    cap: int | None  # most minutes they would give to any one job; None: they set no limit
    money: int  # 0 unless the person gave an amount in some other unit
    picked: tuple[str, ...]  # the words of what they said they would rather take on
    answered: bool  # they answered at least one question

    @property
    def silent(self) -> bool:
        """They said 0 hours: nothing is offered for them."""
        return self.cap == 0


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", text.lower()) if len(w) >= 4}


def limits(told: list[Document]) -> Limits:
    cap: int | None = None
    money = 0
    picked: list[str] = []
    for item in told:
        if item["kind"] == "amount":
            unit = str(item["unit"]).lower()
            if "hour" in unit or unit in {"h", "hr", "hrs"}:
                cap = max(cap or 0, int(item["answer"] * 60))
            else:
                money += int(item["answer"])
        elif item["kind"] == "choice":
            picked.append(str(item["answer"]))
    return Limits(cap, money, tuple(picked), bool(told))


def preferred(need: Document, lim: Limits) -> bool:
    return any(words(p) & words(need["title"]) for p in lim.picked)


def picky(needs: list[Document], lim: Limits) -> bool:
    """They pointed at some need that is in this room, so the rest are what they did not choose."""
    return any(preferred(n, lim) for n in needs)


def estimate(need: Document, lim: Limits, sure: bool) -> tuple[int, Effort]:
    """The rule estimate for one need: quicker and easier for what they chose, slower and
    harder for what they did not (when they chose anything that is in the room)."""
    base = BASE_MINUTES.get(str(need["kind"]), 60)
    effort: Effort = "medium"
    minutes = base
    if sure and preferred(need, lim):
        minutes, effort = max(MIN_MINUTES, base * 3 // 4), "low"
    elif sure:
        minutes, effort = base * 3 // 2, "high"
    if lim.cap is not None:
        minutes = min(minutes, lim.cap)
    return max(MIN_MINUTES, minutes), effort


def rule_offers(needs: list[Document], lim: Limits) -> list[OfferItem]:
    """No model: an offer on every need, each with its own estimate. 0 hours is no offer."""
    if lim.silent:
        return []
    sure = picky(needs, lim)
    out: list[OfferItem] = []
    for need in needs:
        minutes, effort = estimate(need, lim, sure)
        out.append(OfferItem(need_id=need["id"], minutes=minutes, money=0, effort=effort))
    return out


def checked(
    reply: OffersReply | None, needs: list[Document], lim: Limits
) -> list[OfferItem] | None:
    """The model's offers, each clamped to that person's limit for one job; None if none fit."""
    if reply is None or lim.silent:
        return None
    known = {n["id"] for n in needs}
    top = MAX_MINUTES if lim.cap is None else lim.cap
    out: list[OfferItem] = []
    for item in reply.offers:
        if item.need_id not in known or any(o.need_id == item.need_id for o in out):
            continue
        minutes = max(MIN_MINUTES, min(item.minutes, top))
        money = max(0, min(item.money, lim.money))
        out.append(
            OfferItem(need_id=item.need_id, minutes=minutes, money=money, effort=item.effort)
        )
    return out or None


def cover_items(
    needs: list[Document], bare: list[Document], hosted: dict[str, Limits]
) -> dict[str, list[OfferItem]]:
    """Give every bare need an offer from someone who has not said 0 hours, taking turns.

    The guarantee: when at least one hosted person gave more than 0 hours (or no limit), no need
    is left without an offer. Each offer is that person's own estimate for the need.
    """
    able = [who for who, lim in hosted.items() if not lim.silent]
    taken: dict[str, list[OfferItem]] = {}
    for turn, need in enumerate(bare):
        if not able:
            break
        who = able[turn % len(able)]
        minutes, effort = estimate(need, hosted[who], picky(needs, hosted[who]))
        taken.setdefault(who, []).append(
            OfferItem(need_id=need["id"], minutes=minutes, money=0, effort=effort)
        )
    return taken


def span(minutes: int) -> str:
    """ "45 minutes", "3 hours", "1.5 hours"."""
    if minutes < 90:
        return f"{minutes} minutes"
    hours = minutes / 60
    text = f"{hours:.1f}".rstrip("0").rstrip(".")
    return f"{text} hour{'' if text == '1' else 's'}"


def feed_text(items: list[OfferItem], names: dict[str, str], lim: Limits, source: str) -> str:
    if not items:
        why = "you gave it no hours" if lim.silent else "nothing fit what you said"
        return f"Your agent made no offer, because {why}. You can still join a plan later."
    parts = "; ".join(
        f"{names[i.need_id]}, about {span(i.minutes)} ({i.effort} effort)" for i in items
    )
    start = (
        "You skipped the questions, so your agent offered starting guesses: "
        if not lim.answered
        else "Your agent said you could do "
    )
    how = "" if source == "model" else " (fixed rules, no model)"
    return (
        f"{start}{parts}{how}. These are alternatives, not a total: a plan usually asks you "
        "for only some of them, and nothing binds you until you say yes to a plan."
    )
