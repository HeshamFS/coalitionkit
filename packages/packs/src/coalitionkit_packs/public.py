# SPDX-License-Identifier: Apache-2.0
"""Public questions: a question a pack asks every seat whose answer the whole room sees.

Unlike a compared set, the answer is not private. The host publishes it to the room as an
``observe`` from the person's seat, and a question marked ``search`` adds the answer to the
words of that seat's web searches (for example the city a person is in).
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

from .compare import CompareQuestion, Label, SetId

MAX_PUBLIC = 2
WHY = "Everyone in the room sees this answer."


class PublicQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: SetId
    label: Label
    question: CompareQuestion
    search: bool = False
    why: Annotated[str, StringConstraints(max_length=160)] | None = None

    @model_validator(mode="after")
    def _kind(self) -> PublicQuestion:
        if self.question.kind not in {"text", "choice"}:
            raise ValueError("a public question is answered with kind text or choice")
        return self


def check_public(items: list[PublicQuestion]) -> list[PublicQuestion]:
    """At most two public questions, each id once."""
    if len(items) > MAX_PUBLIC:
        raise ValueError(f"a pack declares at most {MAX_PUBLIC} public questions")
    ids = [q.id for q in items]
    twice = sorted({i for i in ids if ids.count(i) > 1})
    if twice:
        raise ValueError(f"public question id declared twice: {', '.join(twice)}")
    return items
