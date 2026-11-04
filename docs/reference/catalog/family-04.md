# Forms and flows

<!-- Written by tools/gen_docs.py. Edit the source, then run it again. -->

14 components in the `coalitionkit/v0_9` catalog.

## AcceptanceForm

Doors: wide, compact.

States: pending, acknowledged, accepted.

Events: `decide(charter) owner-signed`, `leave`.

| Prop | Type | Notes |
|---|---|---|
| `charter` | id | ref |
| `consequence` | string | string |
| `decision_deadline` | datetime | ISO 8601; after it the decision is closed (deadline_exceeded) |
| `diff` | array | [{rule, before, after}] |
| `subject` | subject | {kind, id, revision}: the revision-bound subject of the decision |

## AvailabilityGrid

Doors: wide, compact.

States: empty, painted, imported.

Events: `availability.paint`, `availability.import`.

| Prop | Type | Notes |
|---|---|---|
| `days` | array | [] |
| `slots` | array | per day |
| `source` | enum | manual\|calendar |

## ConsentSeal

Doors: wide, compact.

States: idle, holding, sealed, cancelled.

Events: `decide | commit (owner-signed)`.

| Prop | Type | Notes |
|---|---|---|
| `decision_deadline` | datetime | ISO 8601; after it the decision is closed (deadline_exceeded) |
| `holdMs` | number | 1200 |
| `subject` | subject | {kind, id, revision}: the revision-bound subject of the decision |
| `summary` | string | string |

## DocumentShare

Doors: wide, compact.

States: masked, editing, shared.

Events: `evidence.share(masks)`.

| Prop | Type | Notes |
|---|---|---|
| `document` | id | vault ref |
| `masks` | array | [{region\|field, by}] |
| `purpose` | string | string |
| `preview` | object | Viewer-safe document title and projected rows; hidden values must be omitted. |

## FeedbackForm

Doors: wide, compact.

States: draft, saved.

Events: `feedback.save`.

| Prop | Type | Notes |
|---|---|---|
| `audience` | scope | me\|coalition\|pack authors |
| `questions` | array | [{kind: choice\|scale\|text}] |

## Form

Doors: wide, compact, voice, message.

States: empty, filling, invalid, submitting, sent.

Events: `form.submit(values)`, `form.later`.

| Prop | Type | Notes |
|---|---|---|
| `fields` | array | [{id, kind: text\|number\|money\|datetime\|choice\|multi\|bool\|place\|file, label, required, private: no\|answer-only\|vault, help}] |
| `submit_event` | string | message type |
| `title` | string | string |
| `description` | string | Explanation above the fields. |
| `scope` | string | Submission audience label. |
| `submit_label` | string | Submit button label. |
| `presentation` | enum | Field layout or voice read-back presentation. |
| `conversation` | array | Viewer-safe voice turns; private answers must be omitted. |
| `show_schema` | boolean | Display the field schema alongside the rendered form. |

## LimitField

Doors: wide, compact.

States: set, asked.

Events: `limit.change`.

| Prop | Type | Notes |
|---|---|---|
| `limits` | array | values are read from the local vault, never sent in the tree |
| `queries` | array | [{question, answer, asker, time}] |
| `shared_values` | object | Explicitly shared display values keyed by limit id. Private limit values are never included. |

## NeedForm

Doors: wide, compact, voice.

States: draft, checking, published.

Events: `coalition.need`.

| Prop | Type | Notes |
|---|---|---|
| `audience` | scope | scope |
| `constraints` | array | [{kind, value}] |
| `quantity` | number | int |
| `text` | string | string |

## OfferForm

Doors: wide, compact, voice.

States: draft, published, withdrawn.

Events: `coalition.offer`.

| Prop | Type | Notes |
|---|---|---|
| `conditions` | array | [] |
| `cost` | object | {amount, kind: quote\|estimate} |
| `expires` | datetime | ISO? |
| `target` | enum | need\|task |
| `what` | string | string |
| `target_label` | string | Human-readable target context. |
| `scope` | string | Audience label. |

## OwnerSign

Doors: wide, compact.

States: ready, signing, signed, failed closed.

Events: `sign.confirm`.

| Prop | Type | Notes |
|---|---|---|
| `answer` | enum | bool\|choice |
| `decision_deadline` | datetime | ISO 8601; after it the decision is closed (deadline_exceeded) |
| `kid` | id | owner key |
| `method` | enum | passkey\|hosted key |
| `subject` | subject | {kind, id, revision}: the revision-bound subject of the decision |
| `answer_label` | string | Display label for the selected answer; does not authorize a decision. |
| `subject_label` | string | Human-readable subject label. |
| `device_label` | string | Device display label. |

## Receipt

Doors: wide, compact, message.

States: recorded.

Events: `receipt.verify`, `decide.change`.

| Prop | Type | Notes |
|---|---|---|
| `decision_deadline` | datetime | ISO 8601; after it the decision is closed (deadline_exceeded) |
| `hash` | string | hex |
| `receipt` | object | host-signed |
| `remaining` | array | [participant] |
| `seq` | number | int |
| `subject` | subject | {kind, id, revision}: the revision-bound subject of the decision |

## ReviewStep

Doors: wide, compact.

States: ready, blocked.

Events: `wizard.finish`, `wizard.edit(step)`, `wizard.back`.

| Prop | Type | Notes |
|---|---|---|
| `notice` | string | string |
| `precheck` | object | steward verdict |
| `sections` | array | [{label, summary, editStep}] |

## ValidationSummary

Doors: wide, compact.

States: shown.

Events: `field.focus(id)`.

| Prop | Type | Notes |
|---|---|---|
| `errors` | array | [{field, text}] |

## Wizard

Doors: wide, compact.

States: step, saving, done.

Events: `wizard.next`, `wizard.back`, `wizard.finish`.

| Prop | Type | Notes |
|---|---|---|
| `canSkip` | boolean | bool |
| `current` | id | id |
| `draft` | object | host-saved |
| `steps` | array | [{id, label, fields\|components}] |
