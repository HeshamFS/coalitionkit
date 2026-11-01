# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json

from coalitionkit_contracts import sign_envelope
from coalitionkit_runtime.store import Document
from coalitionkit_steward import PolicySet, parse_policy
from coalitionkit_steward.conditions import StewardContext
from coalitionkit_steward.engine import PackPolicy

from .conftest import World, accepted, error


def bind(world: World, *actions: str) -> None:
    world.host.policy = PackPolicy(
        PolicySet(
            parse_policy(
                f"id: pack-{action}\napplies_to: [coalition.observe]\n"
                f"when:\n  any_text_matches: [protected]\nthen: {action}\nexplain: Review.\n",
                source="pack",
            )
            for action in actions
        ),
        StewardContext(),
    )


def test_pack_block_and_severity(world: World) -> None:
    bind(world, "allow", "escalate", "block")
    result = error(
        world.alice.send("observe", {"source": "chat", "content": "protected"}), "pack_violation"
    )
    assert result["payload"]["detail"] == {"policy_id": "pack-block"}


def test_pack_allow(world: World) -> None:
    bind(world, "allow")
    event = world.alice.envelope("observe", {"source": "chat", "content": "protected"})
    result = accepted(world.host.accept(event, world.alice.auth))
    assert result.accepted["payload"] == event["payload"]
    assert result.accepted["scope"] == event["scope"]


def test_pack_escalation_asks_person_and_holds_message(world: World) -> None:
    bind(world, "escalate")
    requests: list[tuple[Document, str]] = []
    world.host.policy_escalation = lambda event, policy_id, explain: requests.append(
        (event, policy_id)
    )
    before = world.store.read(world.host.coalition_id)
    error(
        world.alice.send("observe", {"source": "chat", "content": "protected"}), "steward_blocked"
    )
    assert requests[0][0]["on_behalf_of"] == "alice"
    assert requests[0][1] == "pack-escalate"
    pending = world.host.pending_policy_reviews("alice")
    assert pending[0]["policy_id"] == "pack-escalate"
    assert pending[0]["question"]
    assert world.host.pending_policy_reviews("bob") == []
    assert world.store.read(world.host.coalition_id) == before


def test_pack_redaction_is_stored_and_projected(world: World) -> None:
    world.host.policy = PackPolicy(
        PolicySet(
            [
                parse_policy(
                    "id: mask\napplies_to: [coalition.observe]\nwhen:\n"
                    "  private_field_in_outbound: true\nthen: redact\nexplain: Mask.\n",
                    source="pack",
                )
            ]
        ),
        StewardContext(private_paths=frozenset({"payload.content"})),
    )
    event = world.alice.envelope("observe", {"source": "chat", "content": "protected"})
    result = accepted(world.host.accept(event, world.alice.auth))
    stored = world.store.read(world.host.coalition_id)[-1]
    assert stored["scope"]["redact"] == ["payload.content"]
    assert "protected" not in json.dumps(world.host.view("bob"))
    replay = accepted(world.host.accept(event, world.alice.auth))
    assert replay.receipt == result.receipt


def test_pack_policy_never_runs_before_signature_check(world: World) -> None:
    def unexpected(event: Document) -> None:
        raise AssertionError("policy ran before core checks")

    world.host.policy = unexpected
    event = world.alice.envelope("observe", {"source": "chat", "content": "protected"})
    event["sig"] = sign_envelope(event, world.bob.agent, "alice")
    error(world.host.accept(event, world.alice.auth), "bad_signature")
