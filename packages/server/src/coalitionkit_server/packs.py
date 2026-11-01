# SPDX-License-Identifier: Apache-2.0
"""Installed packs and their public Genesis metadata."""

import importlib
import re
from pathlib import Path
from typing import Any

from jsonschema.exceptions import ValidationError
from pydantic import BaseModel, ConfigDict

from coalitionkit_contracts.owner import jwk_to_public_key
from coalitionkit_packs import Pack, PackError, load_pack
from coalitionkit_packs.files import take_snapshot
from coalitionkit_packs.signing import verify_snapshot
from coalitionkit_packs.version import core_version
from coalitionkit_runtime import CoalitionHost
from coalitionkit_runtime.lifecycle import State
from coalitionkit_runtime.rules import Refusal, require
from coalitionkit_surfaces import load_catalog

from .adapter import Document


def bound_pack(charter: Document, installed: dict[tuple[str, str], Pack]) -> Pack | None:
    ref = charter.get("pack")
    if ref is None:
        return None
    pack = installed.get((ref["name"], ref["version"]))
    require(pack is not None, "not_authorized")
    return pack


def bind_runtime(host: CoalitionHost, installed: dict[tuple[str, str], Pack]) -> None:
    """Resolve each submission against the installed, exact-version pack snapshot."""

    def check(state: State, event: Document, is_host: bool) -> None:
        kind = event["type"].removeprefix("coalition.")
        body = event["payload"]
        pack = bound_pack(body if kind == "charter" else state.charter, installed)
        if pack is None:
            return
        roles = pack.manifest.roles
        if kind == "charter":
            require(all(role["id"] in roles for role in body["roles"]))
        if not is_host:
            owner = event["on_behalf_of"]
            requested = (
                body["roles_requested"]
                if kind == "join"
                else state.members[owner]["roles_requested"]
            )
            require(bool(requested) and set(requested) <= roles.keys())
            abilities = {ability for role in requested for ability in roles[role].may}
            if kind in {"offer", "commit"}:
                require(kind in abilities)
            elif kind == "decide":
                subject = body["subject"]
                if subject["kind"] == "charter":
                    require("charter" in abilities or "decide" in abilities)
                else:
                    own = (
                        subject["kind"] == "commitment"
                        and state.subject(subject["kind"], subject["id"]).get("sender")
                        == event["sender"]
                    )
                    require("decide" in abilities or ("decide_own" in abilities and own))
        if kind in pack.schemas:
            try:
                pack.validate_schema(kind, body)
            except ValidationError:
                raise Refusal("schema_invalid") from None

    def skills() -> list[str]:
        pack = bound_pack(host.state.charter, installed)
        return list(pack.manifest.skills or []) if pack else []

    host.pack_check = check
    host.skills = skills


class PackRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    version: str


class Suggestion(PackRef):
    why: list[str]


def install_packs(
    folders: list[Path], catalog_file: Path, trusted_keys: dict[str, dict[str, str]]
) -> dict[tuple[str, str], Pack]:
    installed: dict[tuple[str, str], Pack] = {}
    if not folders:
        return installed
    catalog = load_catalog(catalog_file)
    version = core_version()
    keys = {kid: jwk_to_public_key(jwk) for kid, jwk in trusted_keys.items()}
    for folder in folders:
        try:
            pack = load_pack(folder, trusted_keys=keys, core_catalog=catalog, core_version=version)
        except PackError as exc:
            reasons = " ".join(str(exc).splitlines())
            print(f"Pack refused: {folder}: {reasons}", flush=True)
            continue
        key = (pack.name, pack.manifest.version)
        if key in installed:
            print(f"Pack refused: {folder}: duplicate {key[0]} {key[1]}", flush=True)
            continue
        installed[key] = pack
        print(f"Pack: {key[0]} {key[1]} installed", flush=True)
    return installed


def public_pack(pack: Pack) -> Document:
    return {
        "name": pack.name,
        "version": pack.manifest.version,
        "roles": {
            key: role.model_dump(exclude_none=True) for key, role in pack.manifest.roles.items()
        },
        "vocabulary": {
            key: value if isinstance(value, str) else value.model_dump()
            for key, value in pack.vocabulary.items()
        },
        "suggest": pack.manifest.suggest.model_dump() if pack.manifest.suggest else None,
    }


def suggest_pack(goal: str, installed: dict[tuple[str, str], Pack]) -> Suggestion | None:
    """Score distinct matching phrases equally; a tied best score offers no suggestion."""
    candidates: list[Suggestion] = []
    for (name, version), pack in installed.items():
        hints = pack.manifest.suggest
        if hints is None:
            continue
        phrases = dict.fromkeys(text.casefold() for text in [*hints.keywords, *hints.examples])
        why = [
            text
            for text in phrases
            if re.search(r"(?<!\w)" + re.escape(text) + r"(?!\w)", goal.casefold())
        ]
        if why:
            candidates.append(Suggestion(name=name, version=version, why=why))
    candidates.sort(key=lambda item: len(item.why), reverse=True)
    if not candidates or (len(candidates) > 1 and len(candidates[0].why) == len(candidates[1].why)):
        return None
    return candidates[0]


def surface_pack(pack: Pack) -> Document:
    """Unsigned display metadata; never inserted into protocol payloads."""
    return {
        "name": pack.name,
        "version": pack.manifest.version,
        "vocabulary": public_pack(pack)["vocabulary"],
        "views": {
            "order": {
                role: {device: list(names) for device, names in devices.items()}
                for role, devices in pack.views.order.items()
            },
            "components": {
                name: {
                    "props": sorted(spec.props),
                    "required": sorted(spec.required),
                    "doors": sorted(spec.links),
                }
                for name, spec in pack.components.items()
            },
        },
    }


def mint_templates(pack: Pack, coalition: str, trusted_keys: dict[str, dict[str, str]]) -> Any:
    """Read and verify the same bytes before registering data-only Mint entries."""
    module = importlib.import_module("coalitionkit_mint.catalog")
    snapshot = take_snapshot(pack.root)
    verify_snapshot(snapshot, {kid: jwk_to_public_key(jwk) for kid, jwk in trusted_keys.items()})
    registry = module.TemplateRegistry()
    registry.register(
        coalition,
        {
            entry.template: module.PackTemplate(
                snapshot.files[entry.template].decode("utf-8"),
                snapshot.files[entry.tests].decode("utf-8"),
            )
            for entry in pack.manifest.mint or []
        },
    )
    return registry
