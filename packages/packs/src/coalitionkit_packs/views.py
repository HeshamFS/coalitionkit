# SPDX-License-Identifier: Apache-2.0
"""Pack views: extra A2UI component definitions (a catalog extension) and component order."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from coalitionkit_surfaces import Catalog
from coalitionkit_surfaces.catalog import ComponentSpec, PropSpec

from .errors import PackError, Problem, Report
from .manifest import RoleId
from .sections import summarise

Device = Literal["wide", "compact", "message", "voice"]
ComponentName = Annotated[str, StringConstraints(pattern=r"^[A-Z][A-Za-z0-9]{0,63}$")]
_PROP = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
_RESERVED = frozenset({"id", "component"})


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ComponentDef(_Strict):
    props: list[str] = Field(default_factory=list)
    required: list[str] = Field(default_factory=list)
    doors: list[str] = Field(default_factory=list)


class ViewsFile(_Strict):
    components: dict[ComponentName, ComponentDef] = Field(
        default_factory=dict[ComponentName, ComponentDef]
    )
    order: dict[RoleId, dict[Device, list[ComponentName]]] = Field(
        default_factory=dict[RoleId, dict[Device, list[ComponentName]]]
    )


@dataclass(frozen=True)
class Views:
    components: Mapping[str, ComponentSpec] = field(default_factory=dict[str, ComponentSpec])
    order: Mapping[str, Mapping[str, tuple[str, ...]]] = field(
        default_factory=dict[str, Mapping[str, tuple[str, ...]]]
    )


def parse_views(
    data: Any, where: str, core: Catalog, roles: Iterable[str], report: Report
) -> Views:
    try:
        parsed = ViewsFile.model_validate(data)
    except ValidationError as exc:
        report.add("views", where, "; ".join(summarise(exc)))
        return Views()
    specs: dict[str, ComponentSpec] = {}
    for name, definition in parsed.components.items():
        if name in core.components:
            report.add(
                "component_override", f"{where}.{name}", "a pack cannot override a core component"
            )
            continue
        names = [*definition.props, *definition.required, *definition.doors]
        bad = [n for n in names if not _PROP.match(n) or n in _RESERVED]
        if bad:
            report.add("views", f"{where}.{name}", f"bad prop names {sorted(set(bad))}")
            continue
        doors = frozenset(definition.doors)
        props = frozenset(definition.props) | doors
        required = frozenset(definition.required)
        if not required <= props:
            report.add("views", f"{where}.{name}", "requires props it does not allow")
            continue
        # Pack views use the list form; doors become child links, other props accept any value
        # (strings and bound numbers are still enforced by the core validator's walk).
        types = {
            prop: PropSpec("children" if prop in doors else "any", prop in required)
            for prop in sorted(props)
        }
        specs[name] = ComponentSpec(types)
    known = set(core.components) | set(specs)
    role_set = set(roles)
    for role, devices in parsed.order.items():
        if role not in role_set:
            report.add("views", f"{where}.order.{role}", "role is not declared by the pack")
        for device, names_ in devices.items():
            for name in names_:
                if name not in known:
                    report.add(
                        "unknown_component",
                        f"{where}.order.{role}.{device}",
                        f"{name} is not in the core catalog or this pack's components",
                    )
    order = {r: {d: tuple(n) for d, n in ds.items()} for r, ds in parsed.order.items()}
    return Views(specs, order)


def extend_catalog(core: Catalog, packs: Iterable[Mapping[str, ComponentSpec]]) -> Catalog:
    """The core catalog plus the components of the active packs, as a new catalog.

    The core catalog itself is never changed, so a tree that uses a pack component validates
    only against a catalog built from the packs that are active. Two active packs may not
    define the same component.
    """
    merged: dict[str, ComponentSpec] = dict(core.components)
    for components in packs:
        for name, spec in components.items():
            if name in merged:
                raise PackError(
                    [Problem("component_override", name, "component name is already defined")]
                )
            merged[name] = spec
    return Catalog(core.catalog_id, merged)
