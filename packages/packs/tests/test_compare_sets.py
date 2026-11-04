# SPDX-License-Identifier: Apache-2.0
"""The ``compare`` key: named private sets a pack declares, and the loader's clear refusals."""

from pathlib import Path
from typing import Any

import pytest
from packs_support import CORE_VERSION, append, copy_pack, core_catalog
from pydantic import ValidationError

from coalitionkit_packs import PackError, inspect_pack
from coalitionkit_packs.manifest import Manifest

BASE: dict[str, Any] = {
    "name": "pack-test",
    "version": "1.0.0",
    "core": ">=0.1,<0.2",
    "roles": {"member": {"may": ["offer"]}},
    "evals": ["evals/one.yaml"],
}
CHOICE = {
    "id": "colours",
    "label": "Colours we all like",
    "question": {"text": "Which colours suit you?", "kind": "choice", "options": ["a", "b", "c"]},
}


def test_a_set_loads_with_its_defaults() -> None:
    manifest = Manifest.model_validate({**BASE, "compare": [CHOICE]})
    assert manifest.compare is not None
    item = manifest.compare[0]
    assert (item.id, item.mode, item.min_seats) == ("colours", "overlap", None)
    assert item.question.options == ["a", "b", "c"]


def test_count_text_and_slots_load() -> None:
    sets = [
        {
            **CHOICE,
            "id": "words",
            "mode": "count",
            "min_seats": 2,
            "question": {"text": "List a few words", "kind": "text"},
        },
        {**CHOICE, "id": "times", "question": {"text": "Which times?", "kind": "slots"}},
    ]
    manifest = Manifest.model_validate({**BASE, "compare": sets})
    assert [s.question.kind for s in manifest.compare or []] == ["text", "slots"]


@pytest.mark.parametrize(
    ("change", "says"),
    [
        ({"question": {"text": "How much?", "kind": "amount"}}, "an amount is one number"),
        ({"question": {"text": "Pick", "kind": "choice", "options": ["a"]}}, "at least two"),
        ({"question": {"text": "Pick", "kind": "choice", "options": ["a", "a"]}}, "distinct"),
        ({"question": {"text": "Say", "kind": "text", "options": ["a"]}}, "takes no options"),
        ({"question": {"text": "Say", "kind": "scale"}}, "kind"),
        ({"id": "Bad Id"}, "pattern"),
        ({"id": "has:colon"}, "pattern"),
        ({"mode": "all"}, "mode"),
        ({"min_seats": 1}, "min_seats"),
        ({"extra": 1}, "extra"),
    ],
)
def test_bad_sets_are_refused_with_the_rule(change: dict[str, Any], says: str) -> None:
    with pytest.raises(ValidationError) as caught:
        Manifest.model_validate({**BASE, "compare": [{**CHOICE, **change}]})
    assert says in str(caught.value)


def test_ids_once_and_at_most_four() -> None:
    with pytest.raises(ValidationError, match="declared twice: colours"):
        Manifest.model_validate({**BASE, "compare": [CHOICE, CHOICE]})
    many = [{**CHOICE, "id": f"s{i}"} for i in range(5)]
    with pytest.raises(ValidationError, match="at most 4"):
        Manifest.model_validate({**BASE, "compare": many})


def test_the_loader_reports_a_bad_set(tmp_path: Path) -> None:
    folder = copy_pack("pack-alpha", tmp_path)
    append(
        folder / "pack.yaml",
        "compare:\n  - id: sizes\n    label: Sizes\n"
        "    question: { text: How many?, kind: amount }\n",
    )
    with pytest.raises(PackError) as caught:
        inspect_pack(folder, core_catalog=core_catalog(), core_version=CORE_VERSION)
    assert "an amount is one number" in str(caught.value)


def test_the_loader_keeps_a_good_set(tmp_path: Path) -> None:
    folder = copy_pack("pack-alpha", tmp_path)
    append(
        folder / "pack.yaml",
        "compare:\n  - id: colours\n    label: Colours\n    mode: count\n"
        "    question: { text: Which?, kind: choice, options: [a, b, c] }\n",
    )
    pack = inspect_pack(folder, core_catalog=core_catalog(), core_version=CORE_VERSION)
    assert [s.id for s in pack.manifest.compare or []] == ["colours"]
