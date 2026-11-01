# SPDX-License-Identifier: Apache-2.0
"""Installed packs and their public Genesis metadata."""

import importlib
import json
import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, cast

from jsonschema.exceptions import ValidationError
from pydantic import BaseModel, ConfigDict
from referencing.exceptions import Unresolvable

from coalitionkit_contracts import (
    Envelope,
    Scope,
    ScopeSource,
    jwk_thumbprint,
    new_ulid,
    principals,
)
from coalitionkit_contracts.owner import jwk_to_public_key
from coalitionkit_contracts.payloads import Cost, Window
from coalitionkit_gardener import Offer, PlanConfig, PlanSet, Problem, Task, generate_plans
from coalitionkit_packs import Pack, PackError, load_pack
from coalitionkit_packs.files import take_snapshot
from coalitionkit_packs.signing import verify_snapshot
from coalitionkit_packs.version import core_version
from coalitionkit_runtime import CoalitionHost
from coalitionkit_runtime.lifecycle import State
from coalitionkit_runtime.projector import remove_path
from coalitionkit_runtime.rules import Refusal, require
from coalitionkit_runtime.store import Transaction
from coalitionkit_steward import StewardContext
from coalitionkit_steward.conditions import Subject, evaluate_all
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

    with host.store.transaction(host.coalition_id) as tx:
        tx.execute(
            "CREATE TABLE IF NOT EXISTS pack_lessons (name TEXT PRIMARY KEY, pack TEXT NOT NULL, "
            "version TEXT NOT NULL, coalition TEXT NOT NULL, "
            "audience TEXT NOT NULL, body TEXT NOT NULL)"
        )

    with host.store.transaction(host.coalition_id) as tx:
        tx.execute(
            "CREATE INDEX IF NOT EXISTS pack_lessons_pack_version ON pack_lessons (pack, version)"
        )
        tx.execute(
            "CREATE TABLE IF NOT EXISTS pack_policy_outcomes (coalition TEXT NOT NULL, "
            "event_id TEXT NOT NULL, policy_id TEXT NOT NULL, action TEXT NOT NULL, "
            "audience TEXT NOT NULL)"
        )

    def record(tx: Transaction, state: State, event: Document, policy_id: str, action: str) -> None:
        recipients = principals(
            ScopeSource(Scope.model_validate(event["scope"]), event["on_behalf_of"]),
            state.membership(),
        )
        keys = sorted(
            jwk_thumbprint(state.members[p]["owner_key"]) for p in recipients if p in state.members
        )
        # Before the first join there are no readers yet; the charter's audience
        # is resolved with the log when the Coalition dissolves.
        audience = json.dumps(keys) if state.members else None
        tx.execute(
            "INSERT INTO pack_policy_outcomes VALUES (?, ?, ?, ?, ?)",
            (host.coalition_id, event["event_id"], policy_id, action, audience or "null"),
        )

    def refused(event: Document, policy_id: str, action: str) -> None:
        state = host.state
        with host.store.transaction(host.coalition_id) as tx:
            record(tx, state, event, policy_id, action)

    # The host calls check and then policy for the same submission inside one transaction;
    # policy reads the state check was given rather than opening another transaction.
    checked: list[State] = []

    def check(state: State, event: Document, is_host: bool) -> None:
        checked[:] = [state]
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
        if kind in {"need", "offer"} and "ext" in body:
            require(kind in pack.schemas, "schema_invalid")
            try:
                pack.validate_schema(kind, body["ext"])
            except ValidationError, Unresolvable:
                raise Refusal("schema_invalid") from None

    def skills(viewer: str) -> list[Document]:
        state = host.state
        if viewer not in state.members:
            return []
        pack = bound_pack(state.charter, installed)
        result = [_skill(name, text) for name, text in pack.skills.items()] if pack else []
        key = jwk_thumbprint(state.members[viewer]["owner_key"])
        with host.store.transaction(host.coalition_id) as tx:
            rows = tx.execute(
                "SELECT audience, body FROM pack_lessons "
                "WHERE pack = ? AND version = ? ORDER BY name",
                (pack.name if pack else "none", pack.manifest.version if pack else "none"),
            ).fetchall()
        result.extend(json.loads(body) for audience, body in rows if key in json.loads(audience))
        return result

    def followups(state: State, event: Document) -> list[Document]:
        if event["type"] != "coalition.decide" or event["payload"]["subject"]["kind"] != "charter":
            return []
        pack = bound_pack(state.charter, installed)
        if not pack or not all(state.accepted_charter(p) for p in state.charter["deciders"]):
            return []
        charter = next(e for e in state.events.values() if e["type"] == "coalition.charter")
        if any(
            e.get("causation_id") == charter["event_id"] and e["type"] == "coalition.need"
            for e in state.events.values()
        ):
            return []
        drafts: list[Document] = []
        for template in pack.task_templates:
            body: Document = {
                "description": template.description or template.title,
                "requirements": template.requirements,
                "window": template.window.to_wire()
                if template.window
                else {"start": state.charter["created_at"], "end": state.charter["deadline"]},
            }
            if template.ext is not None:
                body["ext"] = template.ext
            draft = host.sign(
                "need",
                body,
                template.scope.to_wire() if template.scope else {"audience": "coalition"},
            )
            draft["causation_id"] = charter["event_id"]
            drafts.append(draft)
        return drafts

    def prepare(
        tx: Transaction, state: State, event: Document, redactions: dict[str, tuple[str, ...]]
    ) -> None:
        if event["type"] != "coalition.dissolve":
            return
        previous = next(
            (e for e in state.events.values() if e["type"] == "coalition.dissolve"), None
        )
        if previous:
            event["payload"]["skills_written"] = previous["payload"]["skills_written"]
            return
        pack = bound_pack(state.charter, installed)
        templates = pack.lessons if pack and pack.lessons else {"lesson.md": GENERIC_LESSON}
        values, audience = lesson_values(state, redactions, host.clock())
        rows = tx.execute(
            "SELECT policy_id, action, audience, event_id FROM pack_policy_outcomes "
            "WHERE coalition = ?",
            (host.coalition_id,),
        ).fetchall()
        for row in rows:
            recipients = json.loads(row[2])
            if row[3] not in state.events:
                audience &= set(recipients or [])
        values["policy_outcomes"] = "; ".join(f"{row[0]}: {row[1]}" for row in rows)
        written: list[str] = []
        for template in templates.values():
            identifier = new_ulid()
            text = re.sub(r"\{\{\s*(\w+)\s*\}\}", lambda m: values.get(m[1], m[0]), template)
            skill = _skill(identifier, text)
            tx.execute(
                "INSERT INTO pack_lessons VALUES (?, ?, ?, ?, ?, ?)",
                (
                    identifier,
                    pack.name if pack else "none",
                    pack.manifest.version if pack else "none",
                    host.coalition_id,
                    json.dumps(sorted(audience)),
                    json.dumps(skill),
                ),
            )
            written.append(identifier)
        event["payload"]["skills_written"] = written

    def policy(event: Document) -> PackPolicyOutcome | None:
        """The bound pack's policies, checked by the host after every core check (spec, step 12)."""
        state = checked[0] if checked else host.state
        pack = bound_pack(state.charter, installed)
        if pack is None:
            return None
        matches = evaluate_all(
            pack.policies,
            Subject.from_envelope(Envelope.model_validate(event)),
            StewardContext(members=frozenset(state.members)),
        )
        if not matches:
            return None
        match = max(matches, key=lambda m: m.policy.severity)
        if match.policy.then == "quarantine":  # refused by the loader; never reached
            raise Refusal("pack_violation", {"policy_id": match.policy.id})
        return PackPolicyOutcome(match.policy.then, match.policy.id, tuple(match.redact))

    host.policy = policy
    host.pack_check = check
    host.skills = skills
    host.followups = followups
    host.prepare = prepare
    host.policy_record = record
    host.policy_refused = refused


@dataclass(frozen=True)
class PackPolicyOutcome:
    action: Literal["allow", "redact", "block", "escalate"]
    policy_id: str
    paths: tuple[str, ...]


def _skill(name: str, text: str) -> Document:
    title = next((line.lstrip("# ") for line in text.splitlines() if line.startswith("# ")), name)
    return {"name": name, "title": title, "text": text}


GENERIC_LESSON = "# Lesson\n" + "\n".join(
    key + ": {{" + key + "}}"
    for key in (
        "goal",
        "members",
        "tasks",
        "allocation",
        "decisions",
        "changes",
        "policy_outcomes",
        "duration",
    )
)


def lesson_values(
    state: State, redactions: dict[str, tuple[str, ...]], now: str
) -> tuple[dict[str, str], set[str]]:
    # Read only log fields; vaults, answers and extension objects never enter a lesson.
    audience = set(state.members)
    bodies: dict[str, list[Document]] = {}
    allocation_visible = True
    for event in state.events.values():
        audience &= set(
            principals(
                ScopeSource(Scope.model_validate(event["scope"]), event["on_behalf_of"]),
                state.membership(),
            )
        )
        body = deepcopy(event["payload"])
        paths = set(event["scope"].get("redact", [])) | set(redactions.get(event["event_id"], ()))
        if event["type"] == "coalition.decide" and paths:
            # A selected assignment must not reveal a withheld decision indirectly.
            allocation_visible = False
        for path in paths:
            remove_path(body, path.split(".")[1:])
        bodies.setdefault(event["type"], []).append(body)
    needs = list(
        {
            str(n.get("need_id", i)): n for i, n in enumerate(bodies.get("coalition.need", []))
        }.values()
    )
    assignments = {
        a["task_id"]: a["assignee"]
        for p in bodies.get("coalition.propose", [])
        for plan in p.get("plans", [])
        for a in plan.get("assignments", [])
        if allocation_visible
        and a.get("assignee") is not None
        and state.tasks.get(a.get("task_id", ""), {}).get("assignee") == a["assignee"]
    }
    values = {
        "goal": str(bodies.get("coalition.charter", [{}])[-1].get("goal", "")),
        "members": str(len(bodies.get("coalition.join", []))),
        "tasks": str(len(needs)) + ": " + "; ".join(str(n.get("description", "")) for n in needs),
        "allocation": "; ".join(
            str(task) + " → " + str(seat) for task, seat in sorted(assignments.items())
        ),
        "decisions": str(len(bodies.get("coalition.decide", []))),
        "changes": "; ".join(str(b.get("change", "")) for b in bodies.get("coalition.ripple", [])),
        "policy_outcomes": "",
        "duration": str(
            datetime.fromisoformat(now)
            - datetime.fromisoformat(bodies.get("coalition.charter", [{}])[-1]["created_at"])
        )
        if "created_at" in bodies.get("coalition.charter", [{}])[-1]
        else "",
    }
    return values, {
        jwk_thumbprint(state.members[p]["owner_key"]) for p in audience if p in state.members
    }


def plan_for(host: CoalitionHost, installed: dict[tuple[str, str], Pack]) -> PlanSet:
    """Plan current open tasks with counted, unexpired offers and the bound strategy."""
    state = host.state
    pack = bound_pack(state.charter, installed)
    strategy = pack.manifest.strategy if pack else None
    tasks = tuple(
        Task(k, tuple(t["requirements"]), Window.model_validate(t["window"]))
        for k, t in state.tasks.items()
        if t["status"] in {"open", "negotiating"}
    )
    if not tasks:
        return PlanSet(())
    ids = {t.task_id for t in tasks}
    offers = tuple(
        Offer(o["owner"], o["target"]["id"], Cost.model_validate(o["cost"]))
        for o in state.offers.values()
        if o.get("counted")
        and o["target"]["id"] in ids
        and datetime.fromisoformat(o["valid_until"]) > datetime.fromisoformat(host.clock())
    )
    return generate_plans(
        Problem(tasks, offers, {p: 1 for p in state.members}),
        config=PlanConfig(
            allocation=strategy.allocation if strategy else None,
            fairness=strategy.fairness or {} if strategy else {},
        ),
    )


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
        "schemas": {
            kind: viewer_schema(pack, kind) for kind in ("need", "offer") if kind in pack.schemas
        },
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


def viewer_schema(pack: Pack, kind: str) -> Document:
    """Bundle references under opaque names, without exposing snapshot file paths."""
    definitions: Document = {}
    names: dict[int, str] = {}

    def visit(node: Any, resolver: Any = None) -> Any:
        resolver = resolver or pack.schema_registry.resolver()
        if isinstance(node, dict):
            result: Document = {}
            for key, value in cast(Document, node).items():
                if key == "$id":
                    continue
                if key in {"const", "default", "examples", "enum"}:
                    result[key] = deepcopy(value)
                elif key in {"$ref", "$dynamicRef"} and isinstance(value, str):
                    resolved = resolver.lookup(value)
                    identity = id(resolved.contents)
                    if identity not in names:
                        name = "ref" + str(len(names))
                        names[identity] = name
                        definitions[name] = {}
                        definitions[name] = visit(resolved.contents, resolved.resolver)
                    result[key] = "#/$defs/" + names[identity]
                else:
                    result[key] = visit(value, resolver)
            return result
        if isinstance(node, list):
            return [visit(value, resolver) for value in cast(list[Any], node)]
        return node

    schema: Document = visit(dict(pack.schemas[kind]))
    if definitions:
        schema.setdefault("$defs", {}).update(definitions)
    return schema


def private_extension(schema: Document, value: Any) -> bool:
    """Inspect every applicable branch before validation can discard annotations."""
    seen: set[tuple[int, int]] = set()

    def check(node: Any, instance: Any) -> bool:
        if not isinstance(node, dict) or not node:
            return False
        obj = cast(Document, node)
        marker = (id(obj), id(instance))
        if marker in seen:
            return False
        seen.add(marker)
        if obj.get("x-private") is True:
            return True
        for keyword in ("$ref", "$dynamicRef"):
            ref = obj.get(keyword, "")
            if ref.startswith("#/$defs/") and check(schema["$defs"][ref.split("/")[-1]], instance):
                return True
        if isinstance(instance, dict):
            for key, child in cast(Document, instance).items():
                properties = obj.get("properties", {})
                patterns = obj.get("patternProperties", {})
                matches = [rule for pattern, rule in patterns.items() if re.search(pattern, key)]
                if key in properties:
                    matches.append(properties[key])
                if not matches:
                    matches.append(obj.get("additionalProperties", {}))
                if any(check(rule, child) for rule in matches):
                    return True
            if any(check(rule, instance) for rule in obj.get("dependentSchemas", {}).values()):
                return True
        if isinstance(instance, list):
            prefix = obj.get("prefixItems", [])
            for index, child in enumerate(cast(list[Any], instance)):
                rule = prefix[index] if index < len(prefix) else obj.get("items", {})
                if check(rule, child) or check(obj.get("contains", {}), child):
                    return True
        return any(
            check(child, instance)
            for keyword in ("allOf", "anyOf", "oneOf")
            for child in obj.get(keyword, [])
        ) or any(check(obj.get(k, {}), instance) for k in ("if", "then", "else"))

    return check(schema, value)
