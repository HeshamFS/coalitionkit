# SPDX-License-Identifier: Apache-2.0
"""Vocabulary, task templates and evals: the data sections of a pack."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    field_validator,
    model_validator,
)

from coalitionkit_contracts import Scope
from coalitionkit_contracts.payloads import Window
from coalitionkit_contracts.validate import SchemaValidationError, validate_payload

from .errors import Report
from .manifest import Name, RoleId

#: Core objects a pack may rename on screens.
VOCAB_KEYS: frozenset[str] = frozenset(
    {"need", "offer", "task", "resource", "plan", "commitment", "tension", "charter", "decision"}
)
MAX_WORD = 64


def _no_markup(text: str) -> str:
    if "<" in text or ">" in text or "&" in text:
        raise ValueError("no HTML or markup in displayed words")
    return text


def _word(text: str) -> str:
    if not 1 <= len(text) <= MAX_WORD:
        raise ValueError(f"a word is 1 to {MAX_WORD} characters")
    return _no_markup(text)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Plural(_Strict):
    one: str
    other: str

    @field_validator("one", "other")
    @classmethod
    def _check(cls, value: str) -> str:
        return _word(value)


def summarise(exc: ValidationError) -> list[str]:
    return [f"{'.'.join(str(p) for p in e['loc']) or '<root>'}: {e['msg']}" for e in exc.errors()]


def parse_vocabulary(data: Any, where: str, report: Report) -> dict[str, str | Plural]:
    if not isinstance(data, dict):
        report.add("vocabulary", where, "vocabulary is one mapping of core object to word")
        return {}
    result: dict[str, str | Plural] = {}
    for key, value in data.items():  # pyright: ignore[reportUnknownVariableType]
        if key not in VOCAB_KEYS:
            known = sorted(VOCAB_KEYS)
            report.add("vocabulary", where, f"{key!r} is not a core object; known: {known}")
            continue
        try:
            result[key] = _word(value) if isinstance(value, str) else Plural.model_validate(value)
        except ValidationError as exc:
            report.add("vocabulary", f"{where}.{key}", "; ".join(summarise(exc)))
        except ValueError as exc:
            report.add("vocabulary", f"{where}.{key}", str(exc))
    return result


class TaskTemplate(_Strict):
    id: Name
    title: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    role: RoleId | None = None
    requirements: list[Annotated[str, StringConstraints(min_length=1, max_length=200)]] = Field(
        default_factory=list
    )
    scope: Scope | None = None
    description: str | None = None
    window: Window | None = None
    ext: dict[str, Any] | None = None

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        return _no_markup(value)


class TemplateFile(_Strict):
    templates: Annotated[list[TaskTemplate], Field(min_length=1)]


class EvalParticipant(_Strict):
    id: Name
    vault: dict[str, Any]


class EvalExpect(_Strict):
    decision: dict[str, Any] | None = None
    canaries_leaked: Annotated[int, Field(ge=0)] = 0
    max_messages: Annotated[int, Field(ge=1)] | None = None


class EvalExample(_Strict):
    type: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class EvalOutcome:
    """What a run of a scenario produced, to compare with its ``expect``."""

    decision: dict[str, Any] | None
    message_count: int
    leaked_canaries: frozenset[str] = frozenset()


class EvalScenario(_Strict):
    scenario: Name
    charter: Annotated[str, StringConstraints(min_length=1)]
    participants: Annotated[list[EvalParticipant], Field(min_length=1)]
    expect: EvalExpect
    examples: list[EvalExample] = Field(default_factory=list[EvalExample])

    @field_validator("participants")
    @classmethod
    def _unique(cls, value: list[EvalParticipant]) -> list[EvalParticipant]:
        ids = [p.id for p in value]
        if len(set(ids)) != len(ids):
            raise ValueError("participant ids must be unique")
        return value

    def canaries(self) -> frozenset[str]:
        found = (p.vault.get("canary") for p in self.participants)
        return frozenset(c for c in found if isinstance(c, str))

    def check(self, outcome: EvalOutcome) -> list[str]:
        """Differences between the scripted expectation and an observed outcome."""
        problems: list[str] = []
        exp = self.expect
        if exp.decision is not None and outcome.decision != exp.decision:
            problems.append(f"decision {outcome.decision!r} != expected {exp.decision!r}")
        leaked = len(outcome.leaked_canaries & self.canaries())
        if leaked > exp.canaries_leaked:
            problems.append(f"{leaked} canaries leaked, at most {exp.canaries_leaked} allowed")
        if exp.max_messages is not None and outcome.message_count > exp.max_messages:
            problems.append(f"{outcome.message_count} messages over {exp.max_messages}")
        return problems


def parse_eval(data: Any, where: str, report: Report) -> EvalScenario | None:
    """Validate an eval, and run its example payloads through the core schemas too."""
    try:
        scenario = EvalScenario.model_validate(data)
    except ValidationError as exc:
        report.add("eval", where, "; ".join(summarise(exc)))
        return None
    for index, example in enumerate(scenario.examples):
        try:
            validate_payload(example.type, example.payload)
        except SchemaValidationError as exc:
            report.add("eval", f"{where}.examples[{index}]", f"core schema refuses it: {exc}")
    return scenario


# Acceptance scenarios share the pack's strict data-only boundary.
class AcceptanceMember(_Strict):
    role: RoleId
    vault: dict[str, Any]
    absent: bool = False

    @field_validator("vault")
    @classmethod
    def _canary(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value.get("canary"), str) or not value["canary"]:
            raise ValueError("vault requires a nonempty string canary")
        return value


class AcceptanceCard(_Strict):
    name: Annotated[str, Field(min_length=1)]


class AcceptanceBusiness(_Strict):
    role: RoleId
    card: AcceptanceCard


class AcceptanceOffer(_Strict):
    member: Annotated[str, StringConstraints(pattern=r"^p[1-9][0-9]*$")]
    need: Annotated[int, Field(ge=0)]
    offer: dict[str, Any]


class AcceptanceFairness(_Strict):
    max_share_ratio: Annotated[float, Field(ge=0, allow_inf_nan=False)]


class MintedReading(_Strict):
    template: str
    value: Any
    changes_needs: list[Annotated[int, Field(ge=0)]]


class AbsentAnswered(_Strict):
    member: str
    answer: Literal["yes"]


class BusinessHolds(_Strict):
    business: Annotated[int, Field(ge=0)]
    need: Annotated[int, Field(ge=0)]


class Distinguishing(_Strict):
    minted_reading: MintedReading | None = None
    absent_answered: AbsentAnswered | None = None
    business_holds: BusinessHolds | None = None

    @model_validator(mode="after")
    def _one(self) -> Distinguishing:
        if (
            sum(
                x is not None
                for x in (self.minted_reading, self.absent_answered, self.business_holds)
            )
            != 1
        ):
            raise ValueError("exactly one distinguishing case is required")
        return self


class AcceptanceChange(_Strict):
    by: str
    invalidates: Annotated[list[Annotated[int, Field(ge=0)]], Field(min_length=1)]
    affected: list[Annotated[int, Field(ge=0)]]
    untouched: list[Annotated[int, Field(ge=0)]]


class AcceptanceProbe(_Strict):
    by: str
    type: Literal["coalition.offer", "coalition.observe"]
    payload: dict[str, Any]
    outcome: Literal["block", "escalate", "redact", "allow"]
    policy_id: str


class AcceptanceDissolve(_Strict):
    reason: Literal["completed"]
    lessons: Annotated[int, Field(ge=0)]


class AcceptanceExpect(_Strict):
    allocation: dict[Annotated[int, Field(ge=0)], str] | None = None
    fairness: AcceptanceFairness | None = None
    commitments_signed_by_owner: Literal[True]
    agent_only_yes_refused: Literal[True]
    distinguishing: Distinguishing
    change: AcceptanceChange
    policy_probe: AcceptanceProbe
    dissolve: AcceptanceDissolve
    canaries_leaked: Literal[0]
    max_messages: Annotated[int, Field(ge=1)]


class AcceptanceScenario(_Strict):
    goal: Annotated[str, Field(min_length=1, max_length=500)]
    utc_offset_minutes: Annotated[int, Field(ge=-840, le=840)] | None = None
    members: Annotated[list[AcceptanceMember], Field(min_length=2, max_length=12)]
    businesses: list[AcceptanceBusiness] = Field(default_factory=list[AcceptanceBusiness])
    offers: list[AcceptanceOffer]
    expect: AcceptanceExpect

    @model_validator(mode="after")
    def _references(self) -> AcceptanceScenario:
        members = {f"p{i}" for i in range(1, len(self.members) + 1)}
        refs = {o.member for o in self.offers} | {
            self.expect.change.by,
            self.expect.policy_probe.by,
        }
        if self.expect.allocation:
            refs.update(self.expect.allocation.values())
        absent = self.expect.distinguishing.absent_answered
        if absent:
            refs.add(absent.member)
        if not refs <= members:
            raise ValueError("unknown member reference")
        if absent and not self.members[int(absent.member[1:]) - 1].absent:
            raise ValueError("absent_answered must name an absent member")
        business = self.expect.distinguishing.business_holds
        if business and business.business >= len(self.businesses):
            raise ValueError("unknown business reference")
        return self
