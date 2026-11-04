# Live and proof

<!-- Written by tools/gen_docs.py. Edit the source, then run it again. -->

18 components in the `coalitionkit/v0_9` catalog.

## ActivityStream

Doors: wide, compact.

States: default.

Events: `item.open(seq)`.

| Prop | Type | Notes |
|---|---|---|
| `filter` | enum | all\|about me\|decisions |
| `items` | array | [{actor, verb, object, time, seq}] |

## CanvasPresence

Doors: wide.

States: acting, idle.

| Prop | Type | Notes |
|---|---|---|
| `cursors` | array | [{actor, kind, target, verb}] |

## ChainView

Doors: wide.

States: intact, broken.

Events: `chain.verify`.

| Prop | Type | Notes |
|---|---|---|
| `entries` | array | [{seq, type, actor, prev_hash, hash, verified}] |
| `genesis` | string | hash |

## ChangedValue

Doors: wide, compact, lens.

States: flash, tinted, seen.

| Prop | Type | Notes |
|---|---|---|
| `after` | any | value |
| `before` | any | value |
| `path` | string | json pointer |

## ConnectionStatus

Doors: wide, compact.

States: live, reconnecting, offline.

Events: `feed.reconnect`.

| Prop | Type | Notes |
|---|---|---|
| `feed` | enum | live\|reconnecting\|offline |
| `latencyMs` | number | int |
| `run` | id | id |

## ErrorNotice

Doors: wide, compact, message, voice.

States: shown.

Events: `error.retry?`.

| Prop | Type | Notes |
|---|---|---|
| `code` | string | spec error code |
| `detail` | object | {} |
| `ref` | id | event? |

## EventRow

Doors: wide, compact.

States: default, selected.

Events: `entry.open`.

| Prop | Type | Notes |
|---|---|---|
| `form` | enum | original\|projection\|receipt-only |
| `seq` | number | int |
| `summary` | string | string |
| `type` | string | message type |

## EvidenceCard

Doors: wide, compact.

States: default, masked.

Events: `evidence.open`.

| Prop | Type | Notes |
|---|---|---|
| `captured_at` | datetime | ISO |
| `kind` | string | string |
| `masks` | array | []? |
| `ref` | id | id |
| `task` | id | ref |
| `verified_by` | id | participant |

## GardenerThinking

Doors: wide, compact, voice.

States: running, done, failed.

| Prop | Type | Notes |
|---|---|---|
| `actor` | id | planner |
| `steps` | array | [{name, state, took}] |

## LiveDocks

Doors: wide.

States: default.

Events: `dock.open(ref)`.

| Prop | Type | Notes |
|---|---|---|
| `docks` | array | [{icon, label, value, ref}] |

## LogStream

Doors: wide, compact.

States: default, gap.

Events: `entry.open(seq)`.

| Prop | Type | Notes |
|---|---|---|
| `entries` | array | [{seq, ts, type, actor, summary, hash, form}] |
| `filter` | array | types |

## MediaWithMasks

Doors: wide, compact.

States: loading, ready.

Events: `mask.label(id, label)`.

| Prop | Type | Notes |
|---|---|---|
| `frame` | number | int? |
| `hidden` | array | [region] |
| `labels` | array | [{mask, label}] editable by the owner |
| `masks` | array | [{polygon\|rle, label, score}] |
| `media_ref` | id | ref |

## ProvenanceTag

Doors: wide, compact, lens, message.

States: default.

| Prop | Type | Notes |
|---|---|---|
| `kind` | enum | measured\|vault\|signed\|model\|estimate |
| `source` | id | ref |

## ReceiptBadge

Doors: wide, compact, message.

States: ok, bad, pending.

Events: `receipt.verify`.

| Prop | Type | Notes |
|---|---|---|
| `seq` | number | int |
| `state` | enum | ok\|bad\|pending |

## RippleBanner

Doors: wide, compact, lens, message.

States: shown, dismissed.

Events: `ripple.open`.

| Prop | Type | Notes |
|---|---|---|
| `ripple` | object | {by, change, invalidated[], untouched[]} |

## StepProgress

Doors: wide, compact, lens.

States: running, deviating, done.

| Prop | Type | Notes |
|---|---|---|
| `eta` | datetime | ISO |
| `measured` | array | series (device) |
| `planned` | array | series |
| `progress` | number | 0-1 |
| `task` | id | ref |

## StewardVerdict

Doors: wide, compact.

States: allow, redact, block, quarantine, escalate.

Events: `verdict.verify`.

| Prop | Type | Notes |
|---|---|---|
| `verdict` | object | {event_id, revision, action, policy_id, redact[], explain, model_audited, issued_at, sig} |

## VerifyPanel

Doors: wide.

States: running, passed, failed.

Events: `verify.run`, `log.download`.

| Prop | Type | Notes |
|---|---|---|
| `checks` | array | [{name, state, detail}] |
| `export` | object | log + receipts + host key |
