# SPDX-License-Identifier: Apache-2.0
"""Loading and the rules the loader rejects."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema.exceptions import ValidationError
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


@pytest.mark.parametrize("action", ["quarantine"])
def test_pack_cannot_quarantine(tmp_path: Path, action: str) -> None:
    root = copy_pack("pack-alpha", tmp_path)
    rewrite(root / "policies" / "flag-keyword.yaml", "then: escalate", f"then: {action}")
    assert rules_of(root) & {"policy_action", "policy"}


def test_pack_can_block(tmp_path: Path) -> None:
    root = copy_pack("pack-alpha", tmp_path)
    rewrite(root / "policies/flag-keyword.yaml", "then: escalate", "then: block")
    assert load(root).policies[0].then == "block"


@pytest.mark.parametrize(
    "ref",
    [
        "file:///outside.json",
        "http://evil/schema.json",
        "../../outside.json",
        "../outside.json",
        "/outside.json",
        "C:/outside.json",
        "//evil/schema.json",
        "%2e%2e/%2e%2e/outside.json",
        "https://evil/schema.json",
        "https://coalitionkit.dev/schemas/unknown.json",
    ],
)
def test_schema_reference_escape_is_reported(tmp_path: Path, ref: str) -> None:
    root = copy_pack("pack-alpha", tmp_path)
    (root / "schemas/need-ext.json").write_text(json.dumps({"$ref": ref}))
    assert "schema_ref" in rules_of(root)


def test_schema_registry_uses_snapshot_and_core(tmp_path: Path) -> None:
    root = copy_pack("pack-alpha", tmp_path)
    sibling = root / "schemas/sibling.json"
    sibling.write_text(json.dumps({"type": "string"}))
    (root / "schemas/need-ext.json").write_text(
        json.dumps(
            {
                "type": "object",
                "properties": {
                    "value": {"$ref": "sibling.json"},
                    "core": {
                        "$ref": "https://coalitionkit.dev/schemas/coalition/v0/common.json#/$defs/ulid"
                    },
                },
                "$defs": {
                    "core": {"$ref": "https://coalitionkit.dev/schemas/coalition/v0/need.json"}
                },
            }
        )
    )
    pack = load(root)
    sibling.write_text(json.dumps({"type": "number"}))
    pack.validate_schema("need", {"value": "still a string"})
    with pytest.raises(ValidationError):
        pack.validate_schema("need", {"value": 5})
    with pytest.raises(ValidationError):
        pack.validate_schema("need", {"core": "invalid"})


def test_transitive_schema_reference_escape_is_reported(tmp_path: Path) -> None:
    root = copy_pack("pack-alpha", tmp_path)
    (root / "schemas/need-ext.json").write_text('{"$ref": "sibling.json"}')
    (root / "schemas/sibling.json").write_text('{"$ref": "file:///outside.json"}')
    assert "schema_ref" in rules_of(root)


def test_schema_literal_data_is_not_rewritten(tmp_path: Path) -> None:
    root = copy_pack("pack-alpha", tmp_path)
    literal = {"$id": "literal", "$ref": "file:///literal"}
    (root / "schemas/need-ext.json").write_text(json.dumps({"const": literal}))
    load(root).validate_schema("need", literal)


@pytest.mark.parametrize("ref", ["#/$defs/missing", "#", "sibling.json"])
def test_unbundleable_schema_is_refused(tmp_path: Path, ref: str) -> None:
    root = copy_pack("pack-alpha", tmp_path)
    (root / "schemas/need-ext.json").write_text(json.dumps({"$ref": ref}))
    (root / "schemas/sibling.json").write_text('{"$ref": "need-ext.json"}')
    assert "schema_ref" in rules_of(root)


def test_viewer_schema_inlines_sibling(tmp_path: Path) -> None:
    from coalitionkit_server.packs import viewer_schema

    root = copy_pack("pack-alpha", tmp_path)
    (root / "schemas/need-ext.json").write_text(
        json.dumps(
            {
                "type": "object",
                "required": ["count"],
                "properties": {"count": {"$ref": "sibling.json"}},
            }
        )
    )
    (root / "schemas/sibling.json").write_text('{"type": "integer", "x-private": true}')
    schema = viewer_schema(load(root), "need")
    assert schema["properties"]["count"] == {"type": "integer", "x-private": True}


def test_bundle_resolves_core_and_local_refs_without_changing_literals(tmp_path: Path) -> None:
    from coalitionkit_packs.loader import bundle_schema

    root = copy_pack("pack-alpha", tmp_path)
    literal = {"$ref": "not-a-schema.json", "$id": "literal"}
    (root / "schemas/need-ext.json").write_text(
        json.dumps(
            {
                "type": "object",
                "$defs": {"count": {"type": "integer", "minimum": 1, "x-private": True}},
                "properties": {
                    "count": {"$ref": "#/$defs/count", "minimum": 3, "x-private": False},
                    "id": {
                        "$ref": "https://coalitionkit.dev/schemas/coalition/v0/common.json#/$defs/ulid"
                    },
                },
                "examples": [literal],
            }
        )
    )
    pack = load(root)
    bundled = bundle_schema(pack.schemas["need"], pack.schema_registry)
    assert bundled["properties"]["id"]["type"] == "string"
    count = bundled["properties"]["count"]["allOf"]  # the reference and its siblings, both kept
    assert count == [
        {"type": "integer", "minimum": 1, "x-private": True},
        {"minimum": 3, "x-private": False},
    ]
    assert bundled["examples"] == [literal]
    from jsonschema import Draft202012Validator

    validator = Draft202012Validator(bundled)
    validator.validate({"count": 3})  # pyright: ignore[reportUnknownMemberType]
    with pytest.raises(ValidationError):
        validator.validate({"count": 2})  # pyright: ignore[reportUnknownMemberType]


def test_nested_dynamic_reference_escape_is_reported(tmp_path: Path) -> None:
    root = copy_pack("pack-alpha", tmp_path)
    (root / "schemas/need-ext.json").write_text(
        json.dumps({"$defs": {"nested": {"$dynamicRef": "file:///outside.json"}}})
    )
    assert "schema_ref" in rules_of(root)


def test_schema_cannot_switch_reference_dialect(tmp_path: Path) -> None:
    root = copy_pack("pack-alpha", tmp_path)
    (root / "schemas/need-ext.json").write_text(
        json.dumps({"$schema": "http://json-schema.org/draft-07/schema#"})
    )
    assert "schema" in rules_of(root)


def test_relative_parent_reference_inside_snapshot(tmp_path: Path) -> None:
    root = copy_pack("pack-alpha", tmp_path)
    (root / "shared.json").write_text('{"type": "string"}')
    (root / "schemas/need-ext.json").write_text('{"$ref": "../shared.json"}')
    pack = load(root)
    pack.validate_schema("need", "valid")
    with pytest.raises(ValidationError):
        pack.validate_schema("need", 1)


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
    rewrite(root / "policies" / "flag-keyword.yaml", "then: escalate", "then: quarantine")
    rewrite(root / "views.yaml", "compact: [StepList]", "compact: [Nowhere]")
    assert rules_of(root) >= {"policy", "unknown_component"}


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


def test_lesson_templates_are_snapshot_text_and_bounded(tmp_path: Path) -> None:
    root = copy_pack("pack-alpha", tmp_path)
    append(root / "pack.yaml", "\nlessons: [lesson.md]\n")
    lesson = root / "lesson.md"
    lesson.write_text("# Lesson\n{{ goal }} {{tasks}}", encoding="utf-8", newline="\n")
    pack = load(root)
    lesson.write_text("changed", encoding="utf-8")
    assert pack.lessons["lesson.md"] == "# Lesson\n{{ goal }} {{tasks}}"
    assert pack.skills["skills/SKILL.md"]
    lesson.write_text("{{unknown}}", encoding="utf-8")
    assert "lessons" in rules_of(root)
    lesson.write_text("x" * (256 * 1024 + 1), encoding="utf-8")
    with pytest.raises(PackError):
        load(root)


def test_task_resource_schemas_load_with_runtime_notice(tmp_path: Path) -> None:
    root = copy_pack("pack-alpha", tmp_path)
    rewrite(
        root / "pack.yaml",
        "schemas: { need: schemas/need-ext.json }",
        "schemas: { task: schemas/need-ext.json, resource: schemas/need-ext.json }",
    )
    with pytest.warns(UserWarning, match="loaded but not applied"):
        pack = load(root)
    assert set(pack.schemas) == {"task", "resource"}


def test_bundle_keeps_a_referenced_closed_object_and_its_siblings_apart(tmp_path: Path) -> None:
    from jsonschema import Draft202012Validator

    from coalitionkit_packs.loader import bundle_schema

    root = copy_pack("pack-alpha", tmp_path)
    base = {
        "type": "object",
        "properties": {"a": {"type": "integer"}},
        "required": ["a"],
        "additionalProperties": False,
    }
    original = {
        "$defs": {"base": base, "size": {"type": "integer", "minimum": 1, "x-private": True}},
        "$ref": "#/$defs/base",
        "properties": {
            "b": {"type": "string"},
            "size": {"$ref": "#/$defs/size", "minimum": 3, "x-private": False},
        },
    }
    (root / "schemas/need-ext.json").write_text(json.dumps(original))
    pack = load(root)
    bundled = bundle_schema(pack.schemas["need"], pack.schema_registry)
    assert "$ref" not in json.dumps(bundled)
    # The web form reads this exact output (apps/web/src/room/extSchema.bundle.test.ts).
    fixture = Path(__file__).parents[3] / "apps/web/src/room/fixtures/bundled-allof.json"
    assert bundled == json.loads(fixture.read_text(encoding="utf-8"))
    cases: tuple[tuple[dict[str, int | str], bool], ...] = (
        ({"a": 1}, True),
        ({}, False),
        ({"a": 1, "b": "x"}, False),
        ({"a": 1, "size": 2}, False),
    )
    for instance, accepted in cases:
        for schema in (pack.schemas["need"], bundled):
            validator = Draft202012Validator(schema, registry=pack.schema_registry)
            assert validator.is_valid(instance) is accepted, (schema, instance)  # pyright: ignore[reportUnknownMemberType]
