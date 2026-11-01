# SPDX-License-Identifier: Apache-2.0
"""Installed packs and their public Genesis metadata."""

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from coalitionkit_contracts.owner import jwk_to_public_key
from coalitionkit_packs import Pack, PackError, load_pack
from coalitionkit_packs.version import core_version
from coalitionkit_surfaces import load_catalog

from .adapter import Document


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
