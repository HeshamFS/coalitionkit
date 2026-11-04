# Coalition and people

<!-- Written by tools/gen_docs.py. Edit the source, then run it again. -->

14 components in the `coalitionkit/v0_9` catalog.

## ActsForGraph

Doors: wide.

States: default.

Events: `agent.inspect(card)`.

| Prop | Type | Notes |
|---|---|---|
| `acting` | id | card? |
| `agents` | array | [{card, cardKid, vendor, runtime, actsFor}] |
| `people` | array | [{participant, ownerKid}] |

## AgentPresence

Doors: wide, compact.

States: live, idle, offline.

| Prop | Type | Notes |
|---|---|---|
| `agent` | id | card |
| `latencyMs` | number | int |
| `pinnedKid` | string | string |
| `state` | enum | live\|idle\|offline |
| `nextReadingAt` | datetime | Next scheduled reading time, displayed beside idle presence. |

## CharterCard

Doors: wide, compact.

States: current, new revision pending.

Events: `charter.history`.

| Prop | Type | Notes |
|---|---|---|
| `revision` | number | int |
| `roles` | array | [{name, min, max}] |
| `rules` | array | [{n, text}] |
| `signedBy` | array | [participant] |

## CoalitionHeader

Doors: wide, compact, lens.

States: default.

Events: `charter.open`.

| Prop | Type | Notes |
|---|---|---|
| `budget` | object | {used, cap} |
| `counts` | object | {people, agents, watchers, tasks, plans} |
| `goal` | string | string |
| `pack` | id | id? |
| `revision` | number | int |
| `title` | string | string |
| `yourState` | enum | tag |

## InviteList

Doors: wide, compact.

States: invited, joined, expired, revoked.

Events: `invite.send`, `invite.revoke`, `invite.changeRole(participant)`.

| Prop | Type | Notes |
|---|---|---|
| `invitations` | array | [{participant?, role, channel, sentAt, expires, state}] |
| `openSeats` | array | [] |

## LeaveControl

Doors: wide, compact.

States: ready, confirming, left.

Events: `coalition.leave`.

| Prop | Type | Notes |
|---|---|---|
| `consequences` | array | [] from host |

## PackChip

Doors: wide, compact.

States: active, available.

Events: `pack.open`.

| Prop | Type | Notes |
|---|---|---|
| `pack` | object | {id, name, version, views[], policies[], authorKid} |

## ParticipantCard

Doors: wide, compact.

States: agreed, acting, owes, watcher, invited, left.

Events: `participant.open`.

| Prop | Type | Notes |
|---|---|---|
| `act` | string | string? |
| `capabilities` | array | [] |
| `participant` | id | ref |
| `roles` | array | [] |
| `seat` | number | 1-5 |
| `state` | enum | agreed\|acting\|owes\|watcher\|invited\|left |

## RoleChip

Doors: wide, compact.

States: held, open.

| Prop | Type | Notes |
|---|---|---|
| `open` | boolean | bool |
| `role` | string | string |

## RoleMatrix

Doors: wide.

States: default.

| Prop | Type | Notes |
|---|---|---|
| `rights` | array | authorization table |
| `roles` | array | [] |

## Roster

Doors: wide.

States: default.

Events: `member.remind(participant)`.

| Prop | Type | Notes |
|---|---|---|
| `members` | array | [{participant, roles, agents, acceptedRevision, load, state}] |

## SeatRing

Doors: wide, lens.

States: default.

Events: `seat.open(participant)`.

| Prop | Type | Notes |
|---|---|---|
| `goal` | string | label |
| `openSeats` | number | int |
| `seats` | array | [{participant, seat, role, state: acting\|owes\|idle\|left}] |

## StageTrack

Doors: wide, compact, lens.

States: done, now, next.

| Prop | Type | Notes |
|---|---|---|
| `current` | binding | path |
| `progress` | number | deciders answered |
| `stages` | array | 7 from spec |

## VendorBadge

Doors: wide, compact, message.

States: default.

| Prop | Type | Notes |
|---|---|---|
| `framework` | string | label (no logo) |
| `transport` | string | A2A\|MCP\|hosted\|minted\|local |
