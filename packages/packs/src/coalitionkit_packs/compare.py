# SPDX-License-Identifier: Apache-2.0
"""Compared sets: a named private set a pack asks every seat for and compares by PSI.

Each entry names the set, the one question every seat is asked for it (in a closed brief kind),
and what the room may learn: the shared values (``overlap``) or only how many there are
(``count``). Values stay in each seat's vault; only the intersection or its size is published.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

SetId = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9-]{0,31}$")]
Label = Annotated[str, StringConstraints(min_length=1, max_length=60, pattern=r"\S")]
Option = Annotated[str, StringConstraints(min_length=1, max_length=60, pattern=r"^\S(.*\S)?$")]
MAX_SETS = 4
MAX_OPTIONS = 12


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CompareQuestion(_Strict):
    """The question each seat is asked. ``choice`` lets a person pick any of the options."""

    text: Annotated[str, StringConstraints(min_length=1, max_length=140, pattern=r"\S")]
    kind: Literal["choice", "amount", "slots", "text"]
    options: Annotated[list[Option], Field(max_length=MAX_OPTIONS)] = []
    why: Annotated[str, StringConstraints(max_length=160)] | None = None

    @model_validator(mode="after")
    def _closed(self) -> CompareQuestion:
        if self.kind == "amount":
            raise ValueError(
                "a compared set needs values to match one by one; an amount is one number, "
                "so ask with kind choice and the amounts as options"
            )
        if self.kind == "choice":
            if len(self.options) < 2:
                raise ValueError("kind choice needs at least two options")
            if len(set(self.options)) != len(self.options):
                raise ValueError("options must be distinct")
        elif self.options:
            raise ValueError(f"kind {self.kind} takes no options")
        return self


class CompareSet(_Strict):
    id: SetId
    label: Label
    question: CompareQuestion
    mode: Literal["overlap", "count"] = "overlap"
    #: How many seats must give values before the room compares; None means every seated person.
    min_seats: Annotated[int, Field(ge=2, le=64)] | None = None


def check_sets(sets: list[CompareSet]) -> list[CompareSet]:
    """At most four sets, each id once."""
    if len(sets) > MAX_SETS:
        raise ValueError(f"a pack declares at most {MAX_SETS} compared sets")
    ids = [s.id for s in sets]
    twice = sorted({i for i in ids if ids.count(i) > 1})
    if twice:
        raise ValueError(f"compared set id declared twice: {', '.join(twice)}")
    return sets
