# SPDX-License-Identifier: Apache-2.0
"""Loading and the rules the loader rejects."""

from __future__ import annotations

from pathlib import Path

import pytest
from packs_support import CORE_VERSION, append, copy_pack, core_catalog, rewrite

from coalitionkit_contracts import Scope
from coalitionkit_packs import (
    EvalOutcome,
    Pack,
    PackError,
    ScopeWidenError,
    check_not_wider,
    extend_catalog,
    inspect_pack,
)
from coalitionkit_surfaces import validate_components


def load(path: Path) -> Pack:
    return inspect_pack(path, core_catalog=core_catalog(), core_version=CORE_VERSION)


def rules_of(path: Path) -> set[str]:
    with pytest.raises(PackError) as caught:
        load(path)
    return caught.value.rules()


def test_alpha_and_beta_load(tmp_path: Path) -> None:
    alpha = load(copy_pack("pack-alpha", tmp_path))
    assert alpha.name == "pack-alpha"
    assert alpha.vocabulary["task"] == "step"
    assert {p.id for p in alpha.policies} == {"alpha-flag-keyword", "alpha-mask-code"}
    assert "StepList" in alpha.components
    assert alpha.views.order["coordinator"]["wide"] == ("Card", "StepList")
    assert alpha.task_templates[0].id == "review-step"
    assert alpha.evals[0].scenario == "two-parties-one-item"
    assert "need" in alpha.schemas
    beta = load(copy_pack("pack-beta", tmp_path))
    assert set(beta.components) == {"ReviewBoard"}


def test_core_range_is_checked(tmp_path: Path) -> None:
    root = copy_pack("pack-beta", tmp_path)
    with pytest.raises(PackError) as caught:
        inspect_pack(root, core_catalog=core_catalog(), core_version="0.2.0")
    assert caught.value.rules() == {"core_range"}


@pytest.mark.parametrize("action", ["block", "quarantine"])
def test_pack_cannot_block_or_quarantine(tmp_path: Path, action: str) -> None:
    root = copy_pack("pack-alpha", tmp_path)
    rewrite(root / "policies" / "flag-keyword.yaml", "then: escalate", f"then: {action}")
    assert rules_of(root) & {"policy_action", "policy"}


def test_pack_policy_cannot_reuse_a_core_id(tmp_path: Path) -> None:
    root = copy_pack("pack-alpha", tmp_path)
    rewrite(root / "policies" / "flag-keyword.yaml", "alpha-flag-keyword", "fairness-cap-exceeded")
    assert rules_of(root) == {"policy_override"}


def test_pack_cannot_override_a_core_component(tmp_path: Path) -> None:
    root = copy_pack("pack-alpha", tmp_path)
    rewrite(root / "views.yaml", "  StepList:", "  Card:")
    assert "component_override" in rules_of(root)


def test_view_order_needs_known_components(tmp_path: Path) -> None:
    root = copy_pack("pack-alpha", tmp_path)
    rewrite(root / "views.yaml", "compact: [StepList]", "compact: [Nowhere]")
    assert rules_of(root) == {"unknown_component"}


def test_pack_components_only_validate_when_active(tmp_path: Path) -> None:
    pack = load(copy_pack("pack-alpha", tmp_path))
    core = core_catalog()
    tree = [
        {"id": "root", "component": "StepList", "title": "t", "children": ["c1"]},
        {"id": "c1", "component": "Card", "title": "x"},
    ]
    assert validate_components(core, tree)  # the core alone refuses
    assert "StepList" not in core.components  # and was never changed
    active = extend_catalog(core, [pack.components])
    assert validate_components(active, tree) == []


def test_two_active_packs_cannot_share_a_component(tmp_path: Path) -> None:
    pack = load(copy_pack("pack-alpha", tmp_path))
    with pytest.raises(PackError):
        extend_catalog(core_catalog(), [pack.components, pack.components])


def test_template_scope_cannot_be_coalition_wide(tmp_path: Path) -> None:
    root = copy_pack("pack-alpha", tmp_path)
    rewrite(
        root / "templates.yaml",
        "{ audience: roles, roles: [coordinator] }",
        "{ audience: coalition }",
    )
    assert rules_of(root) == {"scope_widen"}


def test_template_scope_roles_must_exist(tmp_path: Path) -> None:
    root = copy_pack("pack-alpha", tmp_path)
    rewrite(root / "templates.yaml", "roles: [coordinator] }", "roles: [ghost] }")
    assert rules_of(root) == {"scope_widen"}


def test_scope_narrowing_rules() -> None:
    base = Scope(audience="roles", roles=["a", "b"], redact=["payload.x"])
    check_not_wider(base, Scope(audience="roles", roles=["a"], redact=["payload.x", "payload.y"]))
    for wider in (
        Scope(audience="self", redact=["payload.x"]),  # self is not provably in the audience
        Scope(audience="coalition"),
        Scope(audience="roles", roles=["a", "c"], redact=["payload.x"]),
        Scope(audience="roles", roles=["a"]),
        Scope(audience="participants", participants=["p1"], redact=["payload.x"]),
    ):
        with pytest.raises(ScopeWidenError):
            check_not_wider(base, wider)


@pytest.mark.parametrize("rel", ["../outside.yaml", "/abs.yaml", "a\\b.yaml"])
def test_paths_cannot_leave_the_folder(tmp_path: Path, rel: str) -> None:
    root = copy_pack("pack-alpha", tmp_path)
    rewrite(root / "pack.yaml", "views: views.yaml", f"views: '{rel}'")
    assert "path_escape" in rules_of(root)


def test_symlinks_are_refused(tmp_path: Path) -> None:
    root = copy_pack("pack-alpha", tmp_path)
    outside = tmp_path / "outside.yaml"
    outside.write_text("components: {}\n", encoding="utf-8")
    (root / "views.yaml").unlink()
    try:
        (root / "views.yaml").symlink_to(outside)
    except OSError:
        pytest.skip("symbolic links are not available here")
    assert "path_escape" in rules_of(root)


def test_vault_access_is_refused(tmp_path: Path) -> None:
    root = copy_pack("pack-alpha", tmp_path)
    append(root / "pack.yaml", "vault_access: read\n")
    assert "vault_access" in rules_of(root)


def test_connector_cannot_reach_a_vault(tmp_path: Path) -> None:
    root = copy_pack("pack-beta", tmp_path)
    append(root / "pack.yaml", "connectors:\n  - { name: tool, command: [run, --vault-path, x] }\n")
    assert "vault_access" in rules_of(root)


def test_schema_cannot_take_a_core_id(tmp_path: Path) -> None:
    root = copy_pack("pack-alpha", tmp_path)
    rewrite(
        root / "schemas" / "need-ext.json",
        "https://packs.example.invalid/alpha/need-ext.json",
        "https://coalitionkit.dev/schemas/coalition/v0/need.json",
    )
    assert rules_of(root) == {"schema_override"}


def test_eval_examples_go_through_core_schemas(tmp_path: Path) -> None:
    root = copy_pack("pack-alpha", tmp_path)
    rewrite(
        root / "evals" / "two-parties.yaml",
        'description: "one item needs a review step"',
        "description: 5",
    )
    assert rules_of(root) == {"eval"}


def test_eval_needs_the_required_fields(tmp_path: Path) -> None:
    root = copy_pack("pack-beta", tmp_path)
    rewrite(root / "evals" / "solo.yaml", "charter:", "intent:")
    assert rules_of(root) == {"eval"}


def test_eval_outcome_check(tmp_path: Path) -> None:
    scenario = load(copy_pack("pack-alpha", tmp_path)).evals[0]
    assert scenario.check(EvalOutcome({"slot": "slot-b"}, 12)) == []
    bad = EvalOutcome({"slot": "slot-a"}, 99, frozenset({"C-ALPHA-2"}))
    assert len(scenario.check(bad)) == 3


def test_missing_evals_and_bad_yaml(tmp_path: Path) -> None:
    root = copy_pack("pack-beta", tmp_path)
    rewrite(root / "pack.yaml", "evals: [evals/solo.yaml]", "evals: []")
    assert rules_of(root) == {"manifest"}
    (root / "pack.yaml").write_text("name: [unclosed\n", encoding="utf-8")
    assert rules_of(root) == {"yaml"}


def test_every_problem_is_reported_at_once(tmp_path: Path) -> None:
    root = copy_pack("pack-alpha", tmp_path)
    rewrite(root / "policies" / "flag-keyword.yaml", "then: escalate", "then: block")
    rewrite(root / "views.yaml", "compact: [StepList]", "compact: [Nowhere]")
    assert rules_of(root) >= {"policy_action", "unknown_component"}


def test_pack_words_stay_out_of_the_core_denylist(tmp_path: Path) -> None:
    denylist = Path(__file__).parents[3] / "tools" / "discipline-denylist.txt"
    before = denylist.read_text(encoding="utf-8")
    word = next(
        line.strip() for line in before.splitlines() if line.strip() and not line.startswith("#")
    )
    root = copy_pack("pack-beta", tmp_path)
    rewrite(root / "vocabulary.yaml", "task: step", f"task: {word}")
    assert load(root).vocabulary["task"] == word  # a pack may carry domain words
    assert denylist.read_text(encoding="utf-8") == before  # and the list never changes
    src = Path(__file__).parents[1] / "src" / "coalitionkit_packs"
    assert not any("denylist" in f.read_text(encoding="utf-8") for f in src.glob("*.py"))
