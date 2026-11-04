# SPDX-License-Identifier: Apache-2.0
"""Discipline Packs: load, validate, sign and verify packs without touching the core."""

from .compare import CompareQuestion, CompareSet
from .errors import PackError, Problem
from .loader import Pack, inspect_pack, load_pack
from .manifest import Manifest
from .scopes import ScopeWidenError, check_not_wider, narrow
from .sections import EvalOutcome, EvalScenario, TaskTemplate
from .signing import (
    PackSignature,
    sign_pack,
    verify_pack,
    verify_pack_embedded,
)
from .views import Views, extend_catalog

__all__ = [
    "CompareQuestion",
    "CompareSet",
    "EvalOutcome",
    "EvalScenario",
    "Manifest",
    "Pack",
    "PackError",
    "PackSignature",
    "Problem",
    "ScopeWidenError",
    "TaskTemplate",
    "Views",
    "check_not_wider",
    "extend_catalog",
    "inspect_pack",
    "load_pack",
    "narrow",
    "sign_pack",
    "verify_pack",
    "verify_pack_embedded",
]
