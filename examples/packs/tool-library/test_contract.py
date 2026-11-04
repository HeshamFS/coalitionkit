# SPDX-License-Identifier: Apache-2.0
"""The tool-library example pack loads, validates, signs, runs its evals and passes acceptance.

The pack guides in docs/guides/packs include this pack's files, so this test keeps the docs and
the real loader in step. Run it with:
    uv run pytest examples/packs/tool-library/test_contract.py
"""

import json
import shutil
import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coalitionkit_contracts import Scope
from coalitionkit_contracts.owner import public_key_to_jwk
from coalitionkit_mint.catalog import TemplateRegistry
from coalitionkit_packs import PackError, inspect_pack, load_pack, sign_pack
from coalitionkit_packs.cli import main as pack_cli
from coalitionkit_packs.signing import verify_pack_embedded
from coalitionkit_server.packs import (
    private_extension,
    suggest_pack,
    viewer_schema,
)
from coalitionkit_steward.conditions import StewardContext, Subject, evaluate_all
from coalitionkit_surfaces import load_catalog

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
CATALOG = REPO / "spec/catalog/coalitionkit-v0_9.json"


@pytest.fixture(scope="module")
def pack():
    return inspect_pack(ROOT, core_catalog=load_catalog(CATALOG))


def test_pack_loads_with_every_part(pack) -> None:
    manifest = pack.manifest
    assert (pack.name, manifest.version) == ("tool-library", "1.0.0")
    assert set(manifest.roles) == {"keeper", "lender", "shed"}
    assert set(pack.vocabulary) == {"task", "resource", "need", "offer", "commitment"}
    assert set(pack.schemas) == {"need", "offer"}
    assert [t.id for t in pack.task_templates] == [
        "ladder-saturday",
        "drill-weekend",
        "sprayer-week",
    ]
    assert {p.id for p in pack.policies} == {
        "tool-no-payment-details",
        "tool-safety-sign-off",
        "tool-redact-street-address",
    }
    assert manifest.strategy is not None and manifest.strategy.allocation == "auction"
    assert set(pack.skills) == {"skills/SKILL.md"}
    assert set(pack.lessons) == {"lessons/loans.md", "lessons/handover.md"}
    assert set(pack.components) == {"ShedNote"}
    assert len(pack.evals) == 2
    assert [c.name for c in manifest.connectors or []] == ["shed-desk"]
    assert [m.template for m in manifest.mint or []] == ["mint/bench.json"]
    assert manifest.acceptance == "acceptance.yaml"


def test_validate_command_names_the_pack(capsys: pytest.CaptureFixture[str]) -> None:
    assert pack_cli(["validate", str(ROOT), "--catalog", str(CATALOG)]) == 0
    assert "ok: tool-library 1.0.0 is valid" in capsys.readouterr().out


def test_every_source_file_carries_the_license_line() -> None:
    for path in ROOT.rglob("*"):
        if path.suffix in {".py", ".yaml"} and "__pycache__" not in path.parts:
            assert path.read_text(encoding="utf-8").startswith(
                "# SPDX-License-Identifier: Apache-2.0"
            ), path


def test_goal_suggests_the_pack(pack) -> None:
    chosen = suggest_pack(
        "Share the neighbourhood tools for the weekend repair day",
        {(pack.name, pack.manifest.version): pack},
    )
    assert chosen is not None and chosen.name == "tool-library"


def _subject(payload: dict, scope: Scope | None = None) -> Subject:
    return Subject(
        "message",
        "coalition",
        "event",
        1,
        "coalition.observe",
        "p1",
        scope or Scope(audience="coalition"),
        payload,
    )


@pytest.mark.parametrize(
    ("content", "policy_id", "action", "paths"),
    [
        (
            "Send the deposit to IBAN DE89 3704 0044 0532 0130 00",
            "tool-no-payment-details",
            "block",
            (),
        ),
        ("This ladder is certified safe", "tool-safety-sign-off", "escalate", ()),
        ("Pick it up at 12 Elm Lane", "tool-redact-street-address", "redact", ("payload.content",)),
    ],
)
def test_policy_outcomes(pack, content, policy_id, action, paths) -> None:
    matches = evaluate_all(pack.policies, _subject({"content": content}), StewardContext())
    assert len(matches) == 1
    assert (matches[0].policy.id, matches[0].policy.then, matches[0].redact) == (
        policy_id,
        action,
        paths,
    )


def test_plain_text_matches_no_policy(pack) -> None:
    quiet = _subject({"content": "I can lend the ladder on Saturday morning"})
    assert evaluate_all(pack.policies, quiet, StewardContext()) == []


def test_x_private_fields_are_marked_and_refused_in_ext(pack) -> None:
    schema = viewer_schema(pack, "offer")
    for key in ("shed_key_code", "home_address"):
        assert schema["properties"][key]["x-private"] is True
    assert "x-private" not in schema["properties"]["pickup_note"]
    shared = {"tool_kind": "drill", "condition": "new", "pickup_note": "front porch"}
    pack.validate_schema("offer", shared)
    assert not private_extension(schema, shared)
    # A private value inside ext passes the shape check but the host refuses it.
    leaked = {**shared, "shed_key_code": "4471"}
    pack.validate_schema("offer", leaked)
    assert private_extension(schema, leaked)


def test_pack_extension_is_closed(pack) -> None:
    from jsonschema import ValidationError

    with pytest.raises(ValidationError):
        pack.validate_schema("need", {"tool_kind": "ladder", "colour": "red"})
    with pytest.raises(ValidationError):
        pack.validate_schema("need", {"tool_kind": "hammer"})


def test_templates_carry_valid_need_extensions(pack) -> None:
    for template in pack.task_templates:
        pack.validate_schema("need", template.ext)


def test_lessons_use_only_known_placeholders(pack) -> None:
    text = "\n".join(pack.lessons.values())
    assert "{{goal}}" in text and "{{policy_outcomes}}" in text


def test_mint_templates_register() -> None:
    manifest = inspect_pack(ROOT, core_catalog=load_catalog(CATALOG)).manifest
    module_entries = {}
    from coalitionkit_mint.catalog import PackTemplate

    for entry in manifest.mint or []:
        module_entries[entry.template] = PackTemplate(
            (ROOT / entry.template).read_text(encoding="utf-8"),
            (ROOT / entry.tests).read_text(encoding="utf-8"),
        )
    registry = TemplateRegistry()
    registry.register("c1", module_entries)
    assert registry.resolve("c1", "mint/bench.json").config().template == "resource"


def test_connector_listing_cannot_check_views_without_a_catalog(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # `pack connectors` validates without the core catalog, so a pack with views is refused.
    args = ["connectors", str(ROOT), "--host", "http://127.0.0.1:8000", "--coalition", "c1"]
    assert pack_cli(args) == 1
    assert "core_catalog_missing" in capsys.readouterr().err


def test_connector_is_listed_not_started(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    folder = tmp_path / "pack"
    shutil.copytree(ROOT, folder, ignore=shutil.ignore_patterns("__pycache__", "test_contract.py"))
    manifest = folder / "pack.yaml"
    manifest.write_text(
        "".join(
            line
            for line in manifest.read_text(encoding="utf-8").splitlines(keepends=True)
            if not line.startswith("views:")
        ),
        encoding="utf-8",
    )
    args = ["connectors", str(folder), "--host", "http://127.0.0.1:8000", "--coalition", "c1"]
    assert pack_cli(args) == 0
    row = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert row == {
        "name": "shed-desk",
        "command": ["python", "shed_desk.py"],
        "cwd": "connectors/shed-desk",
    }


def test_connector_signs_like_the_reference_and_offers_by_kind() -> None:
    sys.path.insert(0, str(ROOT / "connectors/shed-desk"))
    try:
        import shed_desk
    finally:
        sys.path.pop(0)
    seed = bytes(range(32))
    key = Ed25519PrivateKey.from_private_bytes(seed)
    assert shed_desk.public_key(seed) == key.public_key().public_bytes_raw()
    assert shed_desk.sign(seed, b"tool") == key.sign(b"tool")
    card = shed_desk.build_card("https://shed.example.invalid", seed)
    assert card["capabilities"]["extensions"][0]["params"]["roles"] == ["shed"]
    offers = shed_desk.offers_for(
        [{"tool_kind": "ladder"}, {"tool_kind": "saw"}, {"tool_kind": "drill"}]
    )
    assert [(o["need"], o["hold"]) for o in offers] == [(0, "ladder-1"), (2, "drill-1")]


def test_sign_verify_and_tamper(tmp_path: Path) -> None:
    folder = tmp_path / "pack"
    shutil.copytree(ROOT, folder, ignore=shutil.ignore_patterns("__pycache__", "test_contract.py"))
    key = Ed25519PrivateKey.generate()
    sign_pack(folder, key, "docs-author")
    assert verify_pack_embedded(folder).kid == "docs-author"
    trusted = {"docs-author": key.public_key()}
    loaded = load_pack(
        folder, trusted_keys=trusted, core_catalog=load_catalog(CATALOG), core_version="0.1.0"
    )
    assert loaded.signature is not None and loaded.signature.pinned
    # An author the caller does not trust does not load, even though the files match.
    other = {"someone-else": Ed25519PrivateKey.generate().public_key()}
    with pytest.raises(PackError) as refused:
        load_pack(folder, trusted_keys=other, core_catalog=load_catalog(CATALOG))
    assert "signature" in refused.value.rules()
    (folder / "vocabulary.yaml").write_text("task: errand\n", encoding="utf-8")
    with pytest.raises(PackError):
        load_pack(folder, trusted_keys=trusted, core_catalog=load_catalog(CATALOG))
    assert public_key_to_jwk(key.public_key(), "docs-author")["kid"] == "docs-author"


def test_evals_pass_without_a_model_key(capsys: pytest.CaptureFixture[str]) -> None:
    assert pack_cli(["eval", str(ROOT)]) == 0
    out = capsys.readouterr().out
    assert "repair-day: pass" in out and "ladder-loan: pass" in out


def test_acceptance_journey_passes_without_a_model_key(capsys: pytest.CaptureFixture[str]) -> None:
    assert pack_cli(["accept", str(ROOT), "--json"]) == 0
    result = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert result["status"] == "pass"
    assert {s["step"] for s in result["steps"]} >= {
        "genesis",
        "allocation",
        "agent_only_yes_refused",
        "policy_probe",
        "dissolve",
        "canaries_leaked",
    }
    assert result["canaries_leaked"] == 0
