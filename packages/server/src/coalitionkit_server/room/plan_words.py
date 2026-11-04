# SPDX-License-Identifier: Apache-2.0
"""Plain words for plans, from facts that code computes.

Code works out who does what in each plan, what each plan favours and what it gives up against
the others, using people's own names. The model only phrases that; if it uses a word from the
internals of planning (points, scores, "best at") or repeats a name, code writes the words itself.
A single plan is named by who does what, with no comparison.
"""

from __future__ import annotations

import re

from ..adapter import Document

NAME_MAX = 40
LINE_MAX = 260
BANNED = re.compile(r"\beffort\b|\bpoints?\b|best at|\bmeasures?\b|objective|\bscores?\b", re.I)
#: What a plan can favour: the key into its numbers, the name it earns, and the phrase for it.
FAVOURS = {
    "total_minutes": ("Quickest", "the least time in all"),
    "busiest_minutes": ("Shared evenly", "the most even load"),
    "effort_points": ("Suits people best", "work going to the people who would rather do it"),
}


def plain(*words: str) -> bool:
    """No internal planning jargon and nothing empty."""
    return all(w.strip() and not BANNED.search(w) for w in words)


def who_does(shown: Document) -> str:
    """ "Mira takes Prepare a plan and Prepare a review; Jonas takes Prepare a budget"."""
    by: dict[str, list[str]] = {}
    for a in shown["assignments"]:
        by.setdefault(a["seat"], []).append(a["need"])
    return "; ".join(f"{who} takes {' and '.join(needs)}" for who, needs in by.items())


def busiest_seat(shown: Document) -> str:
    load: dict[str, int] = {}
    for a in shown["assignments"]:
        load[a["seat"]] = load.get(a["seat"], 0) + a["minutes"]
    return max(load, key=lambda s: load[s], default="")


def favours(shown: Document, everyone: list[Document]) -> list[str]:
    """Keys of what this plan does better than at least one other plan, and no worse than any."""
    out: list[str] = []
    for key in FAVOURS:
        values = [p[key] for p in everyone]
        if len(set(values)) > 1 and shown[key] == min(values):
            out.append(key)
    return out


def gives_up(shown: Document, everyone: list[Document]) -> list[str]:
    """What it costs compared with the best of the other plans, in plain words."""
    others = [p for p in everyone if p["plan_id"] != shown["plan_id"]]
    if not others:
        return []
    out: list[str] = []
    longer = shown["total_minutes"] - min(p["total_minutes"] for p in others)
    if longer > 0:
        out.append(f"takes {longer} minutes longer in all")
    if shown["busiest_minutes"] > min(p["busiest_minutes"] for p in others):
        out.append(f"puts more on {busiest_seat(shown)}")
    if shown["effort_points"] > min(p["effort_points"] for p in others):
        out.append("asks some people for work they would rather not do")
    return out


def differences(shown: Document, everyone: list[Document]) -> list[str]:
    """Who takes something else in the nearest other plan: the plans told side by side."""
    others = [p for p in everyone if p["plan_id"] != shown["plan_id"]]
    if not others:
        return []
    mine = {a["need"]: a["seat"] for a in shown["assignments"]}
    theirs = {a["need"]: a["seat"] for a in others[0]["assignments"]}
    return [
        f"{need}: {who} here, {theirs[need]} there"
        for need, who in mine.items()
        if theirs.get(need) not in (None, who)
    ]


def facts(everyone: list[Document]) -> list[Document]:
    """What the model is told about each plan. No scores, no jargon."""
    out: list[Document] = []
    for shown in everyone:
        out.append(
            {
                "plan_id": shown["plan_id"],
                "who_does_what": who_does(shown),
                "favours": [FAVOURS[k][1] for k in favours(shown, everyone)],
                "gives_up_against_the_others": gives_up(shown, everyone),
                "differs_from_another_plan": differences(shown, everyone),
            }
        )
    return out


def single_name(shown: Document) -> str:
    seats = list(dict.fromkeys(a["seat"] for a in shown["assignments"]))
    if len(seats) == 1:
        return f"{seats[0]} does it"[:NAME_MAX]
    if len(seats) == 2:
        return f"{seats[0]} and {seats[1]} share it"[:NAME_MAX]
    return f"{seats[0]}, {seats[1]} and {len(seats) - 2} more"[:NAME_MAX]


def rule_note(index: int, shown: Document, everyone: list[Document]) -> Document:
    """The words code writes itself: plain, from the same facts."""
    if len(everyone) == 1:
        return {"name": single_name(shown), "line": f"{who_does(shown)}.", "source": "rules"}
    win = favours(shown, everyone)
    if win:
        names = [FAVOURS[k][0] for k in win[:2]]
        name = names[0] if len(names) == 1 else f"{names[0]} and {names[1].lower()}"
    else:
        diff = differences(shown, everyone)
        name = diff[0].split(":")[0] if diff else f"Plan {chr(65 + index)}"
        seat = next((a["seat"] for a in shown["assignments"] if name == a["need"]), "")
        name = f"{seat} takes {name.lower()}" if seat else name
    line = f"{who_does(shown)}."
    if win:
        line += " It favours " + " and ".join(FAVOURS[k][1] for k in win) + "."
    cost = gives_up(shown, everyone)
    if cost:
        line += " Compared with the other plan, it " + " and ".join(cost) + "."
    return {"name": name[:NAME_MAX], "line": line[:LINE_MAX], "source": "rules"}
