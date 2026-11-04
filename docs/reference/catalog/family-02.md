# Shell, doors and templates

<!-- Written by tools/gen_docs.py. Edit the source, then run it again. -->

19 components in the `coalitionkit/v0_9` catalog.

## AccountMenu

Doors: wide, compact.

States: open.

Events: `account.pick(id)`.

| Prop | Type | Notes |
|---|---|---|
| `agents` | array | [] |
| `appearance` | enum | light\|dark\|system |
| `channels` | array | [] |
| `identity` | object | participant + owner key |

## AgentDock

Doors: wide, compact.

States: idle, streaming, tool-call, offline.

Events: `agent.say(text)`.

| Prop | Type | Notes |
|---|---|---|
| `agent` | id | participant |
| `composer` | enum | text\|voice |
| `messages` | array | agent session |

## BoardTemplate

Doors: wide.

States: default.

Events: `card.open(id)`.

| Prop | Type | Notes |
|---|---|---|
| `cards` | array | TaskCard[] |
| `columns` | array | task status |

## ConsentTray

Doors: wide, compact.

States: empty, pending, urgent.

Events: `consent.open(subject)`.

| Prop | Type | Notes |
|---|---|---|
| `requests` | array | [{kind: plan\|tension\|commitment\|charter, subject, revision, deadline}] |

## Deck

Doors: wide.

States: default, collapsed.

Events: `deck.select(id)`.

| Prop | Type | Notes |
|---|---|---|
| `sections` | array | [{id,label,icon,count,tone}] |
| `selected` | id | id |

## EntryComposer

Doors: wide, compact.

States: empty, typing, attached, submitting.

Events: `coalition.create(goal, pack?)`.

| Prop | Type | Notes |
|---|---|---|
| `draft` | string | Initial editable goal text; omitted for an empty composer. |
| `attachments` | array | [ref] → vault |
| `goal` | enum | text\|voice |
| `packs` | array | [pack id] |

## InviteCard

Doors: wide, compact, message.

States: active, used, expired, revoked.

Events: `invite.copy`, `invite.revoke`.

| Prop | Type | Notes |
|---|---|---|
| `channels` | string | link\|QR\|WhatsApp\|card URL |
| `expires` | datetime | ISO |
| `invitation` | object | single-use, bound to participant + card |
| `role` | string | string |

## JoinScreen

Doors: wide, compact.

States: invited, accepting, joined, refused.

Events: `charter.accept → owner-signed decide`, `observe`.

| Prop | Type | Notes |
|---|---|---|
| `charter` | object | {summary, rules[], revision} |
| `inviter` | id | participant |
| `subject` | subject | {kind: charter, id, revision}: the charter revision being accepted |

## LensCard

Doors: lens.

States: shown, acknowledged.

Events: `gesture(name)`.

| Prop | Type | Notes |
|---|---|---|
| `body` | string | ≤1 line |
| `eyebrow` | string | string |
| `gestures` | number | ≤2 |
| `title` | string | ≥22 px |

## MessageDoor

Doors: message.

States: sent, answered, expired.

Events: `reply(n)`, `reply(?)`.

| Prop | Type | Notes |
|---|---|---|
| `title` | string | Coalition label shown beside the channel account name. |
| `choices` | array | [{n, label, value}] |
| `receipt` | string | url |
| `text` | string | ≤1024 chars |

## NotificationCenter

Doors: wide, compact.

States: empty, unread.

Events: `notification.open(ref)`, `notifications.read`.

| Prop | Type | Notes |
|---|---|---|
| `items` | array | [{kind, text, time, ref, read}] |

## PageHeader

Doors: wide, compact.

States: default, sticky.

| Prop | Type | Notes |
|---|---|---|
| `actions` | number | ≤2 |
| `crumbs` | array | [] |
| `eyebrow` | string | string |
| `tabs` | array | ? |
| `title` | string | string |

## PhoneShell

Doors: compact.

States: default.

Events: `tab.select`.

| Prop | Type | Notes |
|---|---|---|
| `header` | child | TopBar |
| `stack` | children | cards |
| `tabs` | string | Now\|Plans\|People\|Agent |

## RoomShell

Doors: wide.

States: live, reconnecting, read-only (watcher).

Events: `deck.select(id)`, `invite.open`, `search.open`.

| Prop | Type | Notes |
|---|---|---|
| `canvas` | child | A2UI root |
| `coalition` | id | ref |
| `deck` | array | [{id,label,count}] |
| `dock` | child | AgentDock |
| `presence` | array | [participant] |
| `stage` | binding | path |
| `tray` | child | ConsentTray |

## SplitView

Doors: wide.

States: default, compact-push.

Events: `split.select(id)`.

| Prop | Type | Notes |
|---|---|---|
| `detail` | children | components |
| `items` | array | [] |
| `selected` | id | id |

## StageBar

Doors: wide, compact, lens.

States: done, now, next.

| Prop | Type | Notes |
|---|---|---|
| `current` | binding | path |
| `stages` | string | Germinate\|Gather\|Negotiate\|Decide\|Act\|Live\|Dissolve |

## TopBar

Doors: wide, compact.

States: default.

| Prop | Type | Notes |
|---|---|---|
| `actions` | number | ≤3 |
| `presence` | array | [participant] |
| `stage` | binding | path |
| `title` | string | string |

## VoiceTurn

Doors: voice.

States: speaking, listening, confirming, timeout.

Events: `voice.choice(value)`, `voice.more`.

| Prop | Type | Notes |
|---|---|---|
| `choices` | array | [{words[], value}] |
| `confirm` | boolean | required for consent |
| `earcon` | string | name |
| `script` | string | ≤3 sentences |

## WiringDrawer

Doors: wide.

States: closed, inspecting, verified, broken.

Events: `wiring.verify`, `wiring.copy`.

| Prop | Type | Notes |
|---|---|---|
| `event_ref` | id | id |
| `projection` | object | viewer's own |
