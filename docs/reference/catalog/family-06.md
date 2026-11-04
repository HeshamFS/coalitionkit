# Needs, offers, tasks and plans

<!-- Written by tools/gen_docs.py. Edit the source, then run it again. -->

15 components in the `coalitionkit/v0_9` catalog.

## AnswerCard

Doors: wide, compact, voice.

States: waiting, answered, declined.

| Prop | Type | Notes |
|---|---|---|
| `answer` | any | value |
| `from` | string | vault |
| `kind` | enum | bool\|number-range\|choice |
| `query` | string | text |
| `task_id` | id | ref? |

## AssignmentRow

Doors: wide, compact, lens.

States: default.

| Prop | Type | Notes |
|---|---|---|
| `assignments` | array | viewer's own [] |
| `fit` | string | vault check |
| `hours` | number | int |
| `share` | number | pct |

## Checklist

Doors: wide, compact.

States: default.

Events: `item.toggle (owner only)`.

| Prop | Type | Notes |
|---|---|---|
| `items` | array | [{text, done, by?, evidence?}] |

## CostSplit

Doors: wide, compact.

States: default.

| Prop | Type | Notes |
|---|---|---|
| `items` | array | [{label, payer, amount, kind}] |
| `rule` | enum | even\|by share\|by use |
| `settlements` | array | [] (display only in v0.1) |

## DependencyGraph

Doors: wide.

States: default, ripple.

Events: `task.open(id)`.

| Prop | Type | Notes |
|---|---|---|
| `changed` | id | task? |
| `edges` | array | [{from, to}] |
| `invalidated` | array | [task] |
| `nodes` | array | [{task, status}] |

## FairnessMeter

Doors: wide, compact.

States: within, over-cap.

| Prop | Type | Notes |
|---|---|---|
| `cap` | number | pct (charter) |
| `rows` | array | [{participant, hours, share, agreedShare}] |

## Gantt

Doors: wide.

States: default, ripple-highlight.

Events: `task.open(id)`.

| Prop | Type | Notes |
|---|---|---|
| `criticalPath` | array | [task] |
| `deadlines` | array | [] |
| `now` | datetime | ISO |
| `rows` | array | [{task, assignee, start, end, status}] |
| `zoom` | enum | hours\|days\|weeks |

## MatchView

Doors: wide.

States: default.

Events: `match.inspect(offer)`.

| Prop | Type | Notes |
|---|---|---|
| `chosen` | id | offer? |
| `need` | id | ref |
| `offers` | array | [{offer, fit, reasons[], blockedBy?}] |

## NeedCard

Doors: wide, compact, message, voice.

States: open, matched, fulfilled, withdrawn.

Events: `need.open`, `need.withdraw`.

| Prop | Type | Notes |
|---|---|---|
| `by` | datetime | ISO |
| `constraints` | array | [] |
| `need_id` | id | id |
| `offers` | number | int |
| `owner` | id | participant |
| `state` | enum | open\|matched\|fulfilled\|withdrawn |
| `text` | string | string |

## ObjectiveBars

Doors: wide, compact.

States: default.

| Prop | Type | Notes |
|---|---|---|
| `objectives` | array | [{name, value, unit, better}] |

## OfferCard

Doors: wide, compact, message, voice.

States: open, accepted, expired, withdrawn.

Events: `offer.accept`, `offer.ask`, `offer.withdraw`.

| Prop | Type | Notes |
|---|---|---|
| `conditions` | array | [] |
| `cost` | object | {amount, kind} |
| `expires` | datetime | ISO |
| `offer_id` | id | id |
| `scope` | scope | scope |
| `state` | enum | open\|accepted\|expired\|withdrawn |
| `target` | enum | need\|task |
| `what` | string | string |

## PlanCompare

Doors: wide, compact.

States: proposed, decided, superseded.

Events: `plan.decide(id) → consent`, `plan.details(id)`.

| Prop | Type | Notes |
|---|---|---|
| `decision_deadline` | datetime | ISO 8601; after it the decision is closed (deadline_exceeded) |
| `plans` | array | [{id, label, subject {kind, id, revision}, objectives{}, assignments[]}] |
| `proposal_set_id` | id | id |
| `rejected` | array | [{plan, reason}] |

## TaskCard

Doors: wide, compact, lens, message.

States: each status.

Events: `task.open`, `task.done`.

| Prop | Type | Notes |
|---|---|---|
| `assignee` | id | participant |
| `deps` | object | {waitsFor[], unblocks[]} |
| `evidence` | id | ref? |
| `status` | enum | open\|negotiating\|proposed\|decided\|committed\|done\|withdrawn |
| `task_id` | id | id |
| `title` | string | string |
| `window` | object | {start, end} |

## TensionCard

Doors: wide, compact, message, voice.

States: open, decided, split → replan, expired.

Events: `tension.choose(option) → consent`.

| Prop | Type | Notes |
|---|---|---|
| `answered` | number | count |
| `deciders` | array | [participant] |
| `decision_deadline` | datetime | ISO 8601; after it the decision is closed (deadline_exceeded) |
| `options` | array | [{id, label, tradeoffs[]}] |
| `subject` | subject | {kind, id, revision}: the revision-bound subject of the decision |
| `task_ids` | array | [] |
| `tension_id` | id | id |

## Timeline

Doors: wide, compact, message.

States: default.

| Prop | Type | Notes |
|---|---|---|
| `items` | array | [{start, end?, title, assignee, state}] |
| `now` | datetime | ISO |
