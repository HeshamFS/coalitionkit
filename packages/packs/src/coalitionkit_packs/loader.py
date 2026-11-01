# SPDX-License-Identifier: Apache-2.0
"""Load a pack folder: every rule checked, every problem reported, nothing partial."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field, replace
from pathlib import Path, PurePosixPath
from posixpath import normpath
from typing import Any, cast
from urllib.parse import unquote, urldefrag

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from pydantic import ValidationError
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from coalitionkit_contracts.validate import load_schemas
from coalitionkit_steward import Policy, PolicyError, PolicySet, core_policies, parse_policy
from coalitionkit_surfaces import Catalog
from coalitionkit_surfaces.catalog import ComponentSpec

from .errors import Report
from .files import MANIFEST, Snapshot, bad_relative_path, take_snapshot
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
from .signing import PackSignature, verify_snapshot
from .version import core_version as installed_core_version
from .version import in_range
from .views import Views, parse_views

#: Quarantine acts on a participant and stays with the core.
FORBIDDEN_PACK_ACTIONS = frozenset({"quarantine"})
SCHEMA_ID_BASE = "https://coalitionkit.dev/schemas/"
SNAPSHOT_BASE = "https://pack-snapshot.invalid/"


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
    schema_registry: Registry[Any] = field(default_factory=lambda: Registry[Any]())

    def validate_schema(self, kind: str, instance: Any) -> None:
        """Validate against the closed, in-memory snapshot registry."""
        validator = Draft202012Validator(self.schemas[kind], registry=self.schema_registry)
        validator.validate(instance)  # pyright: ignore[reportUnknownMemberType]

    @property
    def name(self) -> str:
        return self.manifest.name

    @property
    def components(self) -> Mapping[str, ComponentSpec]:
        return self.views.components


def inspect_pack(
    root: Path | str,
    *,
    core_catalog: Catalog | None = None,
    core_version: str | None = None,
) -> Pack:
    """Validate a pack folder without checking its signature.

    Raises PackError listing every rule broken. Use ``load_pack`` to load for real.
    """
    return _inspect(take_snapshot(root), core_catalog, core_version)


def load_pack(
    root: Path | str,
    *,
    trusted_keys: Mapping[str, Ed25519PublicKey],
    core_catalog: Catalog | None = None,
    core_version: str | None = None,
) -> Pack:
    """Verify the author signature against ``trusted_keys``, then validate and load.

    The folder is read once into a snapshot; the signature is checked on those bytes and the
    same bytes are parsed. A pack that fails either step raises PackError.
    """
    snap = take_snapshot(root)
    signature = verify_snapshot(snap, trusted_keys)
    return replace(_inspect(snap, core_catalog, core_version), signature=signature)


def _inspect(snap: Snapshot, core_catalog: Catalog | None, core_version: str | None) -> Pack:
    report = Report()
    manifest = _read_manifest(snap, report)
    if manifest is None:
        report.raise_if_any()
        raise AssertionError("unreachable")
    version = core_version or installed_core_version()
    if not in_range(version, manifest.core):
        report.add("core_range", MANIFEST, f"core {version} is outside {manifest.core!r}")
    vocab = _vocabulary(snap, manifest, report)
    policies = _policies(snap, manifest, report)
    templates = _templates(snap, manifest, report)
    views = _views(snap, manifest, core_catalog, report)
    evals = _evals(snap, manifest, report)
    schemas, registry = _schemas(snap, manifest, report)
    _other_files(snap, manifest, report)
    report.raise_if_any()
    return Pack(
        snap.root,
        manifest,
        vocab,
        policies,
        templates,
        views,
        evals,
        schemas,
        schema_registry=registry,
    )


def _read_manifest(snap: Snapshot, report: Report) -> Manifest | None:
    data = snap.yaml(MANIFEST, MANIFEST, report)
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


def _vocabulary(snap: Snapshot, manifest: Manifest, report: Report) -> Mapping[str, str | Plural]:
    if manifest.vocabulary is None:
        return {}
    data = snap.yaml(manifest.vocabulary, "vocabulary", report)
    return parse_vocabulary(data, manifest.vocabulary, report) if data is not None else {}


def _policies(snap: Snapshot, manifest: Manifest, report: Report) -> PolicySet:
    core_ids = {p.id for p in core_policies()}
    found: list[Policy] = []
    for rel in manifest.policies or []:
        text = snap.text(rel, f"policies.{rel}", report)
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


def _templates(snap: Snapshot, manifest: Manifest, report: Report) -> tuple[TaskTemplate, ...]:
    if manifest.task_templates is None:
        return ()
    rel = manifest.task_templates
    data = snap.yaml(rel, "task_templates", report)
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


def _views(snap: Snapshot, manifest: Manifest, catalog: Catalog | None, report: Report) -> Views:
    if manifest.views is None:
        return Views()
    if catalog is None:
        report.add(
            "core_catalog_missing",
            "views",
            "views cannot be validated without the core catalog (a pack could override it)",
        )
        return Views()
    data = snap.yaml(manifest.views, "views", report)
    if data is None:
        return Views()
    return parse_views(data, manifest.views, catalog, manifest.roles, report)


def _evals(snap: Snapshot, manifest: Manifest, report: Report) -> tuple[EvalScenario, ...]:
    scenarios: list[EvalScenario] = []
    for rel in manifest.evals:
        data = snap.yaml(rel, f"evals.{rel}", report)
        scenario = parse_eval(data, rel, report) if data is not None else None
        if scenario is not None:
            scenarios.append(scenario)
    names = [s.scenario for s in scenarios]
    if len(set(names)) != len(names):
        report.add("eval", "evals", "duplicate scenario names")
    return tuple(scenarios)


def _schemas(
    snap: Snapshot,
    manifest: Manifest,
    report: Report,
) -> tuple[Mapping[str, Mapping[str, Any]], Registry[Any]]:
    loaded: dict[str, Mapping[str, Any]] = {}
    core = load_schemas()
    resources: dict[str, Any] = dict(core)
    pending = list((manifest.schemas or {}).values())
    seen: set[str] = set()

    def rewrite(node: Any, rel: str) -> None:
        if isinstance(node, dict):
            obj = cast(dict[str, Any], node)
            if obj.get("$schema", "https://json-schema.org/draft/2020-12/schema") != (
                "https://json-schema.org/draft/2020-12/schema"
            ):
                report.add("schema", rel, "pack schemas must use JSON Schema 2020-12")
                obj.pop("$schema", None)
            # IDs cannot redirect relative references away from the signed snapshot.
            identifier = obj.pop("$id", None)
            if str(identifier).startswith(SCHEMA_ID_BASE):
                report.add("schema_override", rel, "a pack schema cannot take a core schema id")
            for keyword in ("$ref", "$dynamicRef"):
                if keyword not in obj:
                    continue
                ref = str(obj[keyword])
                base, fragment = urldefrag(ref)
                if base in core:
                    continue
                decoded = unquote(base)
                target = normpath((PurePosixPath(rel).parent / decoded).as_posix()) if base else rel
                if base and (
                    PurePosixPath(decoded).is_absolute()
                    or any(char in decoded for char in (":", "\\", "\x00"))
                    or bad_relative_path(target)
                    or target not in snap.files
                ):
                    report.add("schema_ref", rel, f"unapproved schema reference {ref!r}")
                    continue
                obj[keyword] = SNAPSHOT_BASE + target + ("#" + fragment if fragment else "")
                if target not in seen:
                    pending.append(target)
            # Only schema-bearing keywords contain schemas; const/default/examples
            # may contain literal objects whose $ref and $id are ordinary data.
            for child in DRAFT202012.subresources_of(obj):
                rewrite(child, rel)

    while pending:
        rel = pending.pop()
        if rel in seen:
            continue
        seen.add(rel)
        data = snap.json(rel, f"schemas.{rel}", report)
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
        schema = deepcopy(schema)
        rewrite(schema, rel)
        schema["$id"] = SNAPSHOT_BASE + rel
        resources[SNAPSHOT_BASE + rel] = schema
    registry: Registry[Any] = Registry()
    registry = registry.with_resources(
        (uri, Resource.from_contents(schema, DRAFT202012)) for uri, schema in resources.items()
    )
    for kind, rel in (manifest.schemas or {}).items():
        if SNAPSHOT_BASE + rel in resources:
            loaded[kind] = resources[SNAPSHOT_BASE + rel]
    return loaded, registry


def _other_files(snap: Snapshot, manifest: Manifest, report: Report) -> None:
    for rel in manifest.skills or []:
        snap.get(rel, f"skills.{rel}", report)
    for entry in manifest.mint or []:
        snap.get(entry.template, "mint.template", report)
        snap.get(entry.tests, "mint.tests", report)
