# SPDX-License-Identifier: Apache-2.0
"""Load a pack folder: every rule checked, every problem reported, nothing partial."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, cast

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from pydantic import ValidationError

from coalitionkit_steward import Policy, PolicyError, PolicySet, core_policies, parse_policy
from coalitionkit_surfaces import CATALOG_ID, Catalog
from coalitionkit_surfaces.catalog import ComponentSpec

from .errors import Report
from .files import (
    MANIFEST,
    load_json_file,
    load_yaml_file,
    read_text,
    resolve,
)
from .manifest import Manifest
from .scopes import PACK_AUDIENCES
from .sections import (
    EvalScenario,
    Plural,
    TaskTemplate,
    TemplateFile,
    parse_eval,
    parse_vocabulary,
    summarise,
)
from .signing import PackSignature, verify_pack
from .version import core_version as installed_core_version
from .version import in_range
from .views import Views, parse_views

#: Actions a pack policy may not use. The spec lets a pack declare block; this lane is stricter.
FORBIDDEN_PACK_ACTIONS = frozenset({"block", "quarantine"})
SCHEMA_ID_BASE = "https://coalitionkit.dev/schemas/"


@dataclass(frozen=True)
class Pack:
    root: Path
    manifest: Manifest
    vocabulary: Mapping[str, str | Plural]
    policies: PolicySet
    task_templates: tuple[TaskTemplate, ...]
    views: Views
    evals: tuple[EvalScenario, ...]
    schemas: Mapping[str, Mapping[str, Any]] = field(default_factory=dict[str, Mapping[str, Any]])
    signature: PackSignature | None = None

    @property
    def name(self) -> str:
        return self.manifest.name

    @property
    def components(self) -> Mapping[str, ComponentSpec]:
        return self.views.components


def _empty_catalog() -> Catalog:
    return Catalog(CATALOG_ID, {})


def inspect_pack(
    root: Path | str,
    *,
    core_catalog: Catalog | None = None,
    core_version: str | None = None,
) -> Pack:
    """Validate a pack folder without checking its signature.

    Raises PackError listing every rule broken. Use ``load_pack`` to load for real.
    """
    base = Path(root)
    report = Report()
    catalog = core_catalog if core_catalog is not None else _empty_catalog()
    manifest = _read_manifest(base, report)
    if manifest is None:
        report.raise_if_any()
        raise AssertionError("unreachable")
    version = core_version or installed_core_version()
    if not in_range(version, manifest.core):
        report.add("core_range", MANIFEST, f"core {version} is outside {manifest.core!r}")
    vocab = _vocabulary(base, manifest, report)
    policies = _policies(base, manifest, report)
    templates = _templates(base, manifest, report)
    views = _views(base, manifest, catalog, report)
    evals = _evals(base, manifest, report)
    schemas = _schemas(base, manifest, report)
    _other_files(base, manifest, report)
    report.raise_if_any()
    return Pack(base, manifest, vocab, policies, templates, views, evals, schemas)


def load_pack(
    root: Path | str,
    *,
    trusted_keys: Mapping[str, Ed25519PublicKey],
    core_catalog: Catalog | None = None,
    core_version: str | None = None,
) -> Pack:
    """Verify the author signature against ``trusted_keys``, then validate and load.

    A pack that fails either step raises PackError and nothing of it is returned.
    """
    base = Path(root)
    signature = verify_pack(base, trusted_keys)
    pack = inspect_pack(base, core_catalog=core_catalog, core_version=core_version)
    return replace(pack, signature=signature)


def _read_manifest(root: Path, report: Report) -> Manifest | None:
    data = load_yaml_file(root, MANIFEST, MANIFEST, report)
    if data is None:
        if not report.problems:
            report.add("manifest", MANIFEST, "empty")
        return None
    if not isinstance(data, dict):
        report.add("manifest", MANIFEST, "pack.yaml holds one mapping")
        return None
    keys = [str(k) for k in cast(dict[Any, Any], data)]
    for key in keys:
        if "vault" in key.lower():
            report.add("vault_access", f"{MANIFEST}.{key}", "a pack cannot ask for vault access")
    try:
        manifest = Manifest.model_validate(data)
    except ValidationError as exc:
        for line in summarise(exc):
            report.add("manifest", MANIFEST, line)
        return None
    for connector in manifest.connectors or []:
        if any("vault" in token.lower() for token in connector.command) or (
            "vault" in connector.name
        ):
            report.add("vault_access", f"connectors.{connector.name}", "no vault access")
    for role, spec in manifest.roles.items():
        if len(set(spec.may)) != len(spec.may):
            report.add("manifest", f"roles.{role}", "duplicate abilities")
    return manifest if not report.problems else None


def _vocabulary(root: Path, manifest: Manifest, report: Report) -> Mapping[str, str | Plural]:
    if manifest.vocabulary is None:
        return {}
    data = load_yaml_file(root, manifest.vocabulary, "vocabulary", report)
    return parse_vocabulary(data, manifest.vocabulary, report) if data is not None else {}


def _policies(root: Path, manifest: Manifest, report: Report) -> PolicySet:
    core_ids = {p.id for p in core_policies()}
    found: list[Policy] = []
    for rel in manifest.policies or []:
        path = resolve(root, rel, f"policies.{rel}", report)
        text = read_text(path, rel, report) if path else None
        if text is None:
            continue
        try:
            policy = parse_policy(text, source="pack")
        except PolicyError as exc:
            report.add("policy", rel, str(exc))
            continue
        if policy.then in FORBIDDEN_PACK_ACTIONS:
            report.add("policy_action", rel, f"a pack policy cannot {policy.then}")
        elif policy.id in core_ids:
            report.add("policy_override", rel, f"policy id {policy.id} belongs to the core")
        else:
            found.append(policy)
    try:
        return PolicySet(found)
    except PolicyError as exc:
        report.add("policy", "policies", str(exc))
        return PolicySet([])


def _templates(root: Path, manifest: Manifest, report: Report) -> tuple[TaskTemplate, ...]:
    if manifest.task_templates is None:
        return ()
    rel = manifest.task_templates
    data = load_yaml_file(root, rel, "task_templates", report)
    if data is None:
        return ()
    try:
        parsed = TemplateFile.model_validate(data)
    except ValidationError as exc:
        report.add("task_templates", rel, "; ".join(summarise(exc)))
        return ()
    seen: set[str] = set()
    for template in parsed.templates:
        where = f"{rel}:{template.id}"
        if template.id in seen:
            report.add("task_templates", where, "duplicate template id")
        seen.add(template.id)
        if template.role is not None and template.role not in manifest.roles:
            report.add("task_templates", where, f"role {template.role} is not declared")
        scope = template.scope
        if scope is None:
            continue
        if scope.audience not in PACK_AUDIENCES:
            report.add("scope_widen", where, f"a pack scope cannot be {scope.audience}")
        for role in scope.roles or []:
            if role not in manifest.roles:
                report.add("scope_widen", where, f"scope names role {role} the pack lacks")
    return tuple(parsed.templates)


def _views(root: Path, manifest: Manifest, catalog: Catalog, report: Report) -> Views:
    if manifest.views is None:
        return Views()
    data = load_yaml_file(root, manifest.views, "views", report)
    if data is None:
        return Views()
    return parse_views(data, manifest.views, catalog, manifest.roles, report)


def _evals(root: Path, manifest: Manifest, report: Report) -> tuple[EvalScenario, ...]:
    scenarios: list[EvalScenario] = []
    for rel in manifest.evals:
        data = load_yaml_file(root, rel, f"evals.{rel}", report)
        scenario = parse_eval(data, rel, report) if data is not None else None
        if scenario is not None:
            scenarios.append(scenario)
    names = [s.scenario for s in scenarios]
    if len(set(names)) != len(names):
        report.add("eval", "evals", "duplicate scenario names")
    return tuple(scenarios)


def _schemas(root: Path, manifest: Manifest, report: Report) -> Mapping[str, Mapping[str, Any]]:
    loaded: dict[str, Mapping[str, Any]] = {}
    for kind, rel in (manifest.schemas or {}).items():
        data = load_json_file(root, rel, f"schemas.{kind}", report)
        if data is None:
            continue
        if not isinstance(data, dict):
            report.add("schema", rel, "a schema is a JSON object")
            continue
        schema: dict[str, Any] = data  # pyright: ignore[reportUnknownVariableType]
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as exc:
            report.add("schema", rel, f"not a valid 2020-12 schema: {exc.message}")
            continue
        if str(schema.get("$id", "")).startswith(SCHEMA_ID_BASE):
            report.add("schema_override", rel, "a pack schema cannot take a core schema id")
        else:
            loaded[kind] = schema
    return loaded


def _other_files(root: Path, manifest: Manifest, report: Report) -> None:
    for rel in manifest.skills or []:
        resolve(root, rel, f"skills.{rel}", report)
    for entry in manifest.mint or []:
        resolve(root, entry.template, "mint.template", report)
        resolve(root, entry.tests, "mint.tests", report)
