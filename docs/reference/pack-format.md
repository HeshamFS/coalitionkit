# Pack format

<!-- Written by tools/gen_docs.py. Edit the source, then run it again. -->

This is the section of [the protocol](protocol.md) that defines Discipline Packs. For a walk through it, see [Write a Discipline Pack](../guides/packs/index.md).

## Discipline Pack format

A pack is a folder of data the loader validates before a Coalition can use it. A pack that fails validation never loads, and the loader's report says which rule it broke.

| Key in `pack.yaml` | Required | Meaning |
|---|---|---|
| `name`, `version` | yes | Unique name and semantic version |
| `core` | yes | The range of core versions it works with, such as `>=0.1,<0.2` |
| `roles` | yes | Role IDs and what each may do: `charter`, `offer`, `decide`, `decide_own`, `commit` |
| `vocabulary` | no | Words shown on screens for core objects (task, resource, need) |
| `schemas` | no | JSON Schemas for the `ext` object of needs and offers (keys `need`, `offer`); the keys `task` and `resource` are accepted for later versions and not applied in v0.1 |
| `policies` | no | Steward policy files |
| `skills` | no | SKILL.md files loaded by agents that join |
| `views` | no | Component order per role and device |
| `mint` | no | Extra Mint templates, each with its own tests |
| `connectors` | no | MCP servers the pack needs, run out of process |
| `strategy` | no | Allocation strategy and fairness settings (see Strategy names below) |
| `suggest` | no | How a host may offer this pack for a goal typed in plain language: `keywords` (lowercase words or short phrases) and `examples` (whole example goals), at most 50 of each. A host that suggests packs MUST also offer "no pack", and a suggestion never binds a pack by itself |
| `lessons` | no | Lesson templates (Markdown with `{{placeholders}}` from a fixed set) the host fills from the log at Dissolve and writes as skills |
| `compare` | no | Named private sets every seat is asked for and the room compares by PSI (see Compared sets below) |
| `evals` | yes | At least one scripted scenario |
| `acceptance` | no | Relative path to the whole-journey acceptance YAML described below |

**Compared sets.** `compare` lists at most four named private sets. The room asks every seated person for each one, keeps the answers in each seat's vault and compares them by PSI, so the room learns only what the set's `mode` allows:

```yaml
compare:
  - id: colours                # lowercase letters, digits and hyphens, starting with a letter; at most 32
    label: Colours we all like
    question:
      text: "Which of these colours would you be happy with?"
      kind: choice             # choice, slots or text
      options: [red, blue, green, yellow, white]
      why: "Only the colours everyone picked are shown."   # optional
    mode: overlap              # overlap (default): the shared values; count: only how many
    min_seats: 3               # optional; default every seated person
```

`question.kind` is one of the closed brief kinds. `choice` needs two to twelve distinct options and lets a person pick any number of them; `slots` offers the room's time slots; `text` takes a short list separated by commas or new lines, and each value is trimmed, its spaces collapsed and lowercased before it is compared. `slots` and `text` take no options. `amount` is refused, because a set is matched value by value. Ids are distinct. The loader refuses any other shape and says which rule it broke.

**Core policies.** The Steward ships `no-regulated-advice`, `no-contact-before-consent`, `no-private-field-in-outbound`, `fairness-cap-exceeded` and `no-contact-details-in-room` (blocks a phone number or email address written into a message to the whole Coalition). Each has a known-answer example the Steward must pass before it starts.

**A policy** is checked deterministically before the Steward's model audit:

```yaml
id: no-regulated-advice
applies_to: [coalition.observe, coalition.offer, coalition.propose]
when:
  any_text_matches_category: [medical_dosage, legal_advice, investment_advice]
then: escalate
explain: "Coordinate the task; leave the advice to a qualified person."
```

**An eval** scripts participants, their private vault contents and the outcome. Each participant MAY name a `role` declared by the pack. If omitted, the default is the first declared role whose abilities include both `offer` and `decide`; if no such role exists, the loader refuses the scenario with an explanatory error:

```yaml
scenario: three-people-one-booking
charter: "Find two hours next week when all three are free and book a room."
participants:
  - id: p1
    vault: { free: ["Tue 10-12", "Wed 14-16"], canary: "C-7Q2X" }
  - id: p2
    vault: { free: ["Wed 14-16", "Thu 09-11"], canary: "C-M41P" }
  - id: p3
    vault: { free: ["Wed 14-16"], canary: "C-0ZK9" }
expect:
  decision: { slot: "Wed 14-16" }
  canaries_leaked: 0
  max_messages: 60
```

**The loader rejects** a pack that declares a policy action other than allow, redact, block or escalate (quarantine acts on a participant, not a message, so it stays with the core); references a component outside the catalog; asks for vault access; points at a file outside its own folder; or changes any protocol schema rather than extending it. The core runs every example and eval in a pack through its own schemas as well as the pack's, so a pack cannot pass with data the core would refuse.

A pack MAY mark an extension property with `"x-private": true`. Such values belong in the member’s vault and MUST NOT be included in a transmitted `ext`. Viewer feed pack metadata includes only the pack’s `need` and `offer` extension schemas under `schemas`; private annotations remain visible to forms. Referenced schemas are bundled through the same closed registry used for validation, inlining sibling files and approved core ids with their `x-private` annotations, without exposing pack file paths. Cyclic or unresolvable references cause the loader to refuse the pack before installation. A viewer without a bound pack receives no pack metadata.

**Binding a pack to a Coalition.** A host installs packs from folders it is given and validates each with the loader; a pack that fails is not installed and the host reports the loader's reasons. A Coalition uses a pack only when its charter names it in `pack: {name, version}`, and only an installed pack with that exact name and version. The binding is fixed for the life of the Coalition: a new charter revision may not change `pack`. When a charter names a pack, the host applies it as follows, and nothing else changes:

| Key | At run time |
|---|---|
| `roles` | The roles the charter may use and what each may do. A member's message needs an ability its role grants; otherwise `not_authorized` |
| `vocabulary` | Words delivered to surfaces with each viewer's projection; never part of any signed payload |
| `schemas` | A pack adds fields to needs and offers only inside their `ext` object. The core schema validates the payload, then the pack's extension validates `ext`; failing it is `schema_invalid`. Without a bound pack, `ext` must be absent. A pack schema may reference only files in its own folder and the core schemas by their `https://coalitionkit.dev/schemas/` ids |
| `policies` | Checked deterministically at step (12) of the check order, after every core check and before the Steward: `block` is `pack_violation` with the policy id; `escalate` holds the message (it does not count), tells the sender it was held with the policy id, and asks the sender's person to review it, who may revise and resubmit; `redact` adds the fields the policy matched (for a text condition, each string field the text matched in) to the event's `scope.redact` before it is stored; `allow` changes nothing. The most severe matching action wins |
| `strategy` | The Gardener's allocation strategy and fairness settings for this Coalition |
| `task_templates` | Needs the Gardener may draft first from the charter |
| `views` | Component order per role and device for composed surfaces; components from the core catalog or the pack's catalog extension |
| `skills`, `lessons` | Skills are offered to every agent that joins (an MCP resource `coalition://{id}/skills` and the join reply). At Dissolve the host fills each lesson template from the log (placeholders: `goal`, `members`, `tasks`, `allocation`, `decisions`, `changes`, `policy_outcomes`, `duration`) and stores the results as skills, scoped no wider than the events they came from, listed in `skills_written`, and offered to agents that join later Coalitions bound to the same pack. A Coalition without lesson templates writes one generic lesson from the same placeholders |
| `mint` | Templates added to the Mint for this Coalition only; each template's tests run before a minted agent is enrolled |
| `compare` | Each seated person's agent asks the declared question beside its own questions, and the answer stays in that seat's vault. A seat whose own agent acts over MCP gives its values by writing the vault key `compare:<id>` (a list of strings) through `POST /v1/agent/vault`. After the offers the host compares each set with the PSI messages (`query`/`answer`, then `match` rounds chained by the first seat that holds values) over the elements `"<id>:<value>"`, and publishes one `coalition.observe` with `source: "document"` whose `content` is `{"common": 1, "set", "values", "compared"}` for `overlap` or `{"common": 1, "set", "count", "compared"}` for `count`. The exchanges between the vaults the host keeps use `reveal: overlap`; in `count` mode only the number leaves the host. With fewer than `min_seats` seats holding values nothing is published. Plans and results may use only the published values |
| `connectors` | Programs the operator runs out of process for this Coalition. A connector gets only a one-use invitation and joins like any business agent with a signed card; it never receives host settings, keys, tokens or access to the store or to vaults |

**Acceptance journey.** The optional `acceptance` key in `pack.yaml` is a relative path to a YAML file. `coalitionkit pack accept <folder> [--live] [--json]` drives an in-process host from Genesis through Dissolve. All structural objects forbid extra keys. Member roles must exist in the pack; member IDs are `p1` through `pN` in join order. Need indices are zero-based task-template or Gardener need indices. Offers are member messages validated against core and pack schemas. Exactly one distinguishing case is specified:

```yaml
goal: "<the sentence typed in Genesis>"
utc_offset_minutes: 60            # optional
members:                          # 2..12
  - role: <role id>
    vault: { <key>: <value>, canary: "<string>" }
    absent: false                 # optional; agent answers, owner must still approve commitments
businesses:                       # optional; business invitation and signed card
  - role: <role id>
    card: { name: "<display name>" }
offers:
  - member: p1
    need: 0
    offer: { ... }
expect:
  allocation: { 0: p1 }           # optional
  fairness: { max_share_ratio: 2 } # optional; plan objective scores
  commitments_signed_by_owner: true
  agent_only_yes_refused: true
  distinguishing:                # exactly one of these three
    minted_reading: { template: "<mint template name>", value: "<value>", changes_needs: [0] }
    # absent_answered: { member: p3, answer: yes }
    # business_holds: { business: 0, need: 0 }
  change:
    by: p2
    invalidates: [0]
    affected: [0]
    untouched: [1]
  policy_probe:
    by: p1
    type: coalition.offer        # or coalition.observe
    payload: { ... }
    outcome: block               # block | escalate | redact | allow
    policy_id: <id>
  dissolve:
    reason: completed
    lessons: 1                   # minimum number of skills_written
  canaries_leaked: 0
  max_messages: 200
```

Each assertion reports a named pass/fail step and reason. Canary scanning covers the log, every viewer's projection and replay, Steward inputs, agent channels and connector exchanges. Live member agents use the gateway and report calls, tokens, latency and cost; `--live` without `COALITIONKIT_META_API_KEY` reports `not run (no key)`.

**Strategy names.** `strategy.allocation` names one of the host's built-in strategies, and `strategy.fairness` may set only the keys that strategy reads:

| Name | What it does | Fairness keys |
|---|---|---|
| `auction` | Each task goes to the offer with the lowest cost plus a fairness weight times the bidder's share after winning (Contract-Net) | `weight` (0 to 10), `max_ratio` (hours per share unit, greater than 0), `minute_value` (whole number of at least 1, the value of a minute against money) |
| `match` | Reserved for a later version; not usable by packs in v0.1 (the host cannot read PSI overlaps) | none |
| `vote` | Reserved for a later version; not usable by packs in v0.1 (the host has no ballots) | none |

Any other name, or a fairness key the named strategy does not read, is refused when the pack is installed.

A pack never widens a scope, never reads a vault, never changes a core schema, and never sees another Coalition. The kit contains no pack: packs are data the host is given at run time.
