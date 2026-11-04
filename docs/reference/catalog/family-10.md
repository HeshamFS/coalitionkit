# Mint and machines

<!-- Written by tools/gen_docs.py. Edit the source, then run it again. -->

9 components in the `coalitionkit/v0_9` catalog.

## AttackTests

Doors: wide, compact.

States: running, passed, failed.

Events: `tests.rerun`.

| Prop | Type | Notes |
|---|---|---|
| `tests` | array | [{name, kind: bounds\|injection\|egress\|rate\|failsafe, state, log}] |

## CaptureCard

Doors: compact.

States: ready, recording, done.

Events: `capture.start`, `capture.stop → MintPipeline`.

| Prop | Type | Notes |
|---|---|---|
| `masks` | array | live SAM [{label, score}] |
| `narration` | id | audio |
| `tips` | array | [] |
| `video` | id | vault ref |

## DeviceAlarm

Doors: wide, compact, lens, message.

States: firing, acknowledged, cleared.

Events: `alarm.stop`, `alarm.ack`.

| Prop | Type | Notes |
|---|---|---|
| `autoAction` | string | string? |
| `device` | id | agent |
| `duration` | number | s |
| `reading` | number | value |
| `threshold` | number | value |
| `firedAt` | datetime | Time the alarm fired. |
| `ripple` | string | Summary of affected tasks and notified participants. |
| `unit` | string | Unit of the reading and threshold. |

## DeviceReading

Doors: wide, compact.

States: live, stale.

Events: `reading.export`.

| Prop | Type | Notes |
|---|---|---|
| `annotations` | array | [] |
| `limits` | array | [] |
| `planned` | array | series? |
| `series` | array | [{t, value, confidence}] |
| `source` | id | agent |
| `unit` | string | string |

## EdgeReaderStatus

Doors: wide, compact.

States: reading, low-confidence, lost.

| Prop | Type | Notes |
|---|---|---|
| `confidence` | number | 0-1 |
| `fallback` | string | rule |
| `framesKept` | string | none default |
| `rate` | number | fps |
| `source` | enum | camera\|serial\|vendor app |
| `sourceLabel` | string | Human-readable label of the reader source. |
| `confidenceWindow` | number | Window in seconds over which confidence was measured. |

## MintPipeline

Doors: wide.

States: running, failed, ready to publish.

Events: `stage.open(artifact)`.

| Prop | Type | Notes |
|---|---|---|
| `cost` | string | meter |
| `elapsed` | number | s |
| `stages` | array | [{name: capture\|read\|design\|code\|attack\|publish, state, took, detail, artifacts[]}] |
| `elapsedPlaceholder` | string | Explicit placeholder when elapsed time has not been measured. |

## MintedAgentCard

Doors: wide, compact.

States: live, offline, updating.

Events: `agent.logs`, `agent.offline`, `agent.remint`.

| Prop | Type | Notes |
|---|---|---|
| `agent` | object | {name, version, runtime, owner} |
| `health` | string | state |
| `readings` | array | [] |
| `tools` | array | [] |

## PublishApproval

Doors: wide, compact.

States: locked, ready, published.

Events: `publish → owner-signed`, `decline`.

| Prop | Type | Notes |
|---|---|---|
| `coalitions` | array | [] |
| `spec` | object | {reads[], acts[] with bounds, never[]} |
| `tests` | object | summary |

## ScheduleTwin

Doors: wide, compact.

States: default.

Events: `slot.hold → offer`.

| Prop | Type | Notes |
|---|---|---|
| `machines` | array | [{name, owner, bookings[{start, end, mine?}]}] |
