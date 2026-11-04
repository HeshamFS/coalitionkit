# Channels, ending and memory

<!-- Written by tools/gen_docs.py. Edit the source, then run it again. -->

13 components in the `coalitionkit/v0_9` catalog.

## ChannelHandoff

Doors: lens, compact, message.

States: offered, opened, expired.

Events: `handoff.open`.

| Prop | Type | Notes |
|---|---|---|
| `from` | string | door |
| `reason` | enum | money\|identity\|too long |
| `subject` | subject | ref + revision |
| `to` | string | door |
| `summary` | string | Human-readable summary of the request being handed off. |
| `actionLabel` | string | Human-readable action to review at the destination. |

## ChannelSettings

Doors: wide, compact.

States: default.

Events: `channel.set(kind, level)`, `quiet.set`.

| Prop | Type | Notes |
|---|---|---|
| `channels` | array | [{kind, level}] |
| `overrides` | array | per coalition |
| `quiet` | object | {from, to, tz} |

## CoalitionArchive

Doors: wide, compact.

States: default, empty.

Events: `archive.open(id)`.

| Prop | Type | Notes |
|---|---|---|
| `items` | array | [{coalition, pack, ended, outcome, yourCost, log}] |

## CostMeter

Doors: wide, compact.

States: ok, warning 80%, stopped 100%.

| Prop | Type | Notes |
|---|---|---|
| `budget` | number | money |
| `rows` | array | [{role, model, tokens, cost}] |
| `total` | number | money |

## DissolveSummary

Doors: wide, compact.

States: default.

Events: `log.download`, `results.open`.

| Prop | Type | Notes |
|---|---|---|
| `contributions` | array | [{participant, tasks, hours}] |
| `cost` | string | meter |
| `counts` | object | {tasks, decisions, replans} |
| `goal` | string | string |
| `log` | id | sealed ref |
| `outcome` | enum | reached\|partly\|not\|deadline |

## DoorMatrix

Doors: wide.

States: default.

| Prop | Type | Notes |
|---|---|---|
| `doors` | array | [wide\|compact\|message\|voice\|lens\|mcp-app] |
| `target` | string | the catalog component whose doors are shown |

## ExportControl

Doors: wide, compact.

States: default, exporting, wiped.

Events: `export.zip`, `vault.wipe`.

| Prop | Type | Notes |
|---|---|---|
| `items` | array | [{kind, size, included}] |

## LessonReview

Doors: wide, compact.

States: suggested, saved.

Events: `lessons.save`.

| Prop | Type | Notes |
|---|---|---|
| `lessons` | array | [{text, from[], scope: private\|shareable, kind}] |

## MessageTemplate

Doors: message.

States: sent, replied.

Events: `reply(id)`.

| Prop | Type | Notes |
|---|---|---|
| `params` | array | [] (no private fields) |
| `quickReplies` | number | ≤3 |
| `template` | string | id + version |

## MetricTile

Doors: wide, compact.

States: measured, not run yet.

| Prop | Type | Notes |
|---|---|---|
| `context` | string | string |
| `label` | string | string |
| `run` | id | ref |
| `unit` | string | string |
| `value` | number | measured? |
| `placeholder` | string | Explicit placeholder for an unmeasured value; never a measurement. |

## NotificationCard

Doors: push.

States: delivered, grouped.

Events: `notification.open`.

| Prop | Type | Notes |
|---|---|---|
| `body` | string | ≤90 chars, no private values |
| `link` | string | deep link |
| `title` | string | coalition |
| `ageLabel` | string | Relative notification time, for example now or 2 h. |

## Scorecard

Doors: wide.

States: default.

| Prop | Type | Notes |
|---|---|---|
| `tiles` | array | [MetricTile] |

## SkillCard

Doors: wide, compact.

States: draft, shared.

Events: `coalition.create(from skill)`.

| Prop | Type | Notes |
|---|---|---|
| `name` | string | string |
| `roles` | array | [] |
| `rules` | array | [] |
| `source` | string | coalition |
| `templates` | array | [] |
| `usedCount` | number | Number of times this reusable pattern was used. |
| `summary` | string | Short description of the reusable workflow. |
