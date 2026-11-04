# Privacy and consent

<!-- Written by tools/gen_docs.py. Edit the source, then run it again. -->

16 components in the `coalitionkit/v0_9` catalog.

## ApprovalButton

Doors: wide, compact, lens.

States: ready, disabled, signing.

Events: `approve → owner-signed`.

| Prop | Type | Notes |
|---|---|---|
| `consequence` | string | what saying yes binds you to |
| `decision_deadline` | datetime | ISO 8601; after it the decision is closed (deadline_exceeded) |
| `disabledReason` | string | string? |
| `label` | string | string |
| `subject` | subject | {kind, id, revision}: the revision-bound subject of the decision |

## CanaryMonitor

Doors: wide.

States: clean, leak.

| Prop | Type | Notes |
|---|---|---|
| `canaries` | number | int |
| `found` | number | int (must be 0) |
| `runs` | number | int |
| `surfaces` | array | [] |

## CommitmentCard

Doors: wide, compact.

States: pending, approved, suspended, withdrawn.

Events: `commit.approve`, `commit.withdraw`.

| Prop | Type | Notes |
|---|---|---|
| `assignee` | id | participant |
| `commitment_id` | id | member ULID |
| `decision_deadline` | datetime | ISO 8601; after it the decision is closed (deadline_exceeded) |
| `due` | datetime | ISO |
| `status` | enum | pending\|approved\|suspended\|withdrawn\|superseded |
| `subject` | subject | {kind, id, revision}: the revision-bound subject of the decision |
| `task` | id | ref |
| `charterRevision` | number | Bound current charter revision required to resume a suspended commitment. |

## ConsentCard

Doors: wide, compact, message, voice.

States: open, answered, stale, expired.

Events: `decide(yes|no) owner-signed`, `compare`.

| Prop | Type | Notes |
|---|---|---|
| `consequence` | string | what saying yes binds you to |
| `consequenceOfNo` | string | string |
| `cost` | string | string |
| `decision_deadline` | datetime | ISO 8601; after it the decision is closed (deadline_exceeded) |
| `subject` | subject | {kind, id, revision}: the revision-bound subject of the decision |
| `summary` | string | string |
| `yourPart` | string | string |
| `acceptLabel` | string | Optional affirmative button label, including a human-readable subject name; defaults to Accept. |

## DecisionLog

Doors: wide, compact.

States: default.

Events: `entry.open`.

| Prop | Type | Notes |
|---|---|---|
| `entries` | array | [{time, participant, subject, revision, answer, reason?, seq, verified}] |

## DisclosureLadder

Doors: wide, compact.

States: default.

Events: `disclosure.raise → consent`, `disclosure.lower`.

| Prop | Type | Notes |
|---|---|---|
| `buckets` | array | []? |
| `field` | id | id |
| `level` | enum | none\|bool\|range\|exact |
| `overrides` | array | [{audience, level}] |

## DurableConsent

Doors: wide, compact.

States: default.

Events: `grant.allow`, `grant.revoke`.

| Prop | Type | Notes |
|---|---|---|
| `grants` | array | [{grantee, action, scope, expires, signed}] |
| `requests` | array | [] |

## OverlapView

Doors: wide.

States: running, done.

| Prop | Type | Notes |
|---|---|---|
| `mode` | enum | intersection\|count-only |
| `parties` | array | [] |
| `result` | enum | slots\|count |
| `run` | id | log ref |
| `tokens` | array | truncated |

## PrivateField

Doors: wide, compact, voice.

States: masked, revealed.

Events: `field.reveal`.

| Prop | Type | Notes |
|---|---|---|
| `display` | string | the masked text shown; the value itself stays in the local vault |
| `policy` | string | chip |
| `reveal` | number | seconds |
| `label` | string | Visible field label; never the private value. |
| `unit` | string | Unit or cadence displayed beside the masked value. |

## ProjectionNote

Doors: wide, compact.

States: default.

Events: `projection.verify`.

| Prop | Type | Notes |
|---|---|---|
| `removed` | number | count |
| `source` | object | {event_id, seq, prev_hash, hash} |
| `viewerSpecific` | boolean | bool |

## RedactionDiff

Doors: wide, compact.

States: default.

Events: `redaction.appeal`.

| Prop | Type | Notes |
|---|---|---|
| `delivered` | string | text |
| `original` | string | sender only |
| `verdict` | object | {action, policy_id, paths} |

## ScopeBadge

Doors: wide, compact, message.

States: default.

| Prop | Type | Notes |
|---|---|---|
| `audience` | scope | host\|self\|task:x\|role:y\|coalition\|public |
| `redact` | array | [path] |

## StaleNotice

Doors: wide, compact, message.

States: shown.

Events: `subject.review`.

| Prop | Type | Notes |
|---|---|---|
| `currentRevision` | number | int |
| `decision_deadline` | datetime | ISO 8601; after it the decision is closed (deadline_exceeded) |
| `diff` | array | [] |
| `subject` | subject | {kind, id, revision}: the revision-bound subject of the decision |
| `yourRevision` | number | int |

## VaultCard

Doors: wide, compact.

States: default.

Events: `vault.export`, `vault.wipe`.

| Prop | Type | Notes |
|---|---|---|
| `answersToday` | number | int |
| `categories` | array | [{name, count, policy: answer-only\|psi\|masked\|never}] |
| `location` | enum | device\|self-hosted |

## VoteTally

Doors: wide, compact.

States: open, closed.

| Prop | Type | Notes |
|---|---|---|
| `answered` | number | count |
| `answers` | array | after close |
| `deciders` | array | [] |
| `decision_deadline` | datetime | ISO 8601; after it the decision is closed (deadline_exceeded) |
| `outcome` | enum | decided\|refused\|split\|expired |
| `rule` | string | string |
| `subject` | subject | {kind, id, revision}: the revision-bound subject of the decision |

## WhatOthersKnow

Doors: wide, compact.

States: default.

Events: `view.export`.

| Prop | Type | Notes |
|---|---|---|
| `rows` | array | [{participant, knows[], notKnows[], because}] |
