# SPDX-License-Identifier: Apache-2.0
"""The three members of the interop run: who they are, what their vaults hold, which model runs."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from members.adk_member import AdkBrain, ScriptedAdkLlm, meta_model
from members.hosted_member import HostedBrain, PolicyTransport
from members.kit.brain import MAX_TOKENS, REASONING_EFFORT, Brain
from members.kit.policy import Terms, VaultPolicy
from members.langgraph_member import LangGraphBrain, ScriptedChat, meta_chat_model

from coalitionkit_models import CostMeter, ModelGateway, Settings, load_price_table

META_BASE_URL = "https://api.meta.ai/v1"
META_MODEL = "muse-spark-1.3"
KEY_VARIABLE = "COALITIONKIT_META_API_KEY"

Framework = Literal["adk", "langgraph", "hosted"]


@dataclass(frozen=True)
class MemberSpec:
    name: str
    framework: Framework


SPECS: tuple[MemberSpec, ...] = (
    MemberSpec("p1", "adk"),
    MemberSpec("p2", "langgraph"),
    MemberSpec("p3", "hosted"),
)

#: label -> (minutes, money in minor units, effort); neutral numbers, no real-world content.
_SHEETS: dict[str, dict[str, Terms]] = {
    "p1": {"t1": Terms(30, 5, "low"), "t2": Terms(45, 8, "medium"), "t3": Terms(20, 3, "low")},
    "p2": {"t1": Terms(40, 6, "low"), "t2": Terms(25, 4, "low"), "t3": Terms(35, 7, "high")},
    "p3": {"t1": Terms(35, 6, "medium"), "t2": Terms(30, 5, "low"), "t3": Terms(30, 4, "medium")},
}
#: Tasks each vault says yes to; the rest are answered no and never offered.
_FEASIBLE: dict[str, frozenset[str]] = {
    "p1": frozenset({"t1", "t3"}),
    "p2": frozenset({"t1", "t2"}),
    "p3": frozenset({"t1", "t2", "t3"}),
}
_CANARY: dict[str, str] = {"p1": "C-7Q2X", "p2": "C-M41P", "p3": "C-0ZK9"}


def vault_for(name: str) -> VaultPolicy:
    return VaultPolicy(_SHEETS[name], _CANARY[name], _FEASIBLE[name])


@dataclass(frozen=True)
class Mode:
    """Scripted (no network) or live (the Meta API, key from the environment only)."""

    live: bool

    @property
    def label(self) -> str:
        return "live" if self.live else "scripted"

    def api_key(self) -> str:
        key = os.environ.get(KEY_VARIABLE, "")
        if not key:
            raise RuntimeError(f"{KEY_VARIABLE} is not set")
        return key


@dataclass
class BuiltBrain:
    brain: Brain
    meter: CostMeter | None = None


def _gateway(mode: Mode, meter: CostMeter) -> ModelGateway:
    if mode.live:
        settings = Settings(
            meta_api_key=mode.api_key(),  # type: ignore[arg-type]
            meta_base_url=META_BASE_URL,
            hosted_agent_model=META_MODEL,
        )
        return ModelGateway(settings, meter=meter)
    return ModelGateway(Settings(), transport=PolicyTransport(), meter=meter)


def build_brain(spec: MemberSpec, mode: Mode, coalition_id: str) -> BuiltBrain:
    """The framework brain for a member, on the live model or a scripted one."""
    if spec.framework == "adk":
        if mode.live:
            llm = meta_model(mode.api_key(), META_BASE_URL, META_MODEL, MAX_TOKENS)
            return BuiltBrain(AdkBrain(llm, REASONING_EFFORT))
        return BuiltBrain(AdkBrain(ScriptedAdkLlm()))
    if spec.framework == "langgraph":
        if mode.live:
            chat = meta_chat_model(
                mode.api_key(), META_BASE_URL, META_MODEL, MAX_TOKENS, REASONING_EFFORT
            )
            return BuiltBrain(LangGraphBrain(chat, META_MODEL))
        return BuiltBrain(LangGraphBrain(ScriptedChat(), "scripted-chat"))
    meter = CostMeter(load_price_table())
    return BuiltBrain(HostedBrain(_gateway(mode, meter), coalition_id, spec.name), meter)
