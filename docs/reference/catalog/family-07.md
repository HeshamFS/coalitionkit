# Places and time

<!-- Written by tools/gen_docs.py. Edit the source, then run it again. -->

9 components in the `coalitionkit/v0_9` catalog.

## AgendaList

Doors: wide, compact, voice.

States: default.

Events: `item.action`.

| Prop | Type | Notes |
|---|---|---|
| `day` | datetime | date |
| `items` | array | [{time, title, state, action?}] |

## ArrivalCard

Doors: lens, message, compact.

States: arrived.

| Prop | Type | Notes |
|---|---|---|
| `arrivedAt` | datetime | ISO |
| `next` | string | string |
| `others` | array | [{participant, state}] |
| `place` | id | ref |

## CalendarWeek

Doors: wide.

States: default.

Events: `event.open`, `calendar.export`.

| Prop | Type | Notes |
|---|---|---|
| `events` | array | [{kind: task\|deadline\|private-busy, start, end, assignee}] |
| `range` | object | week |

## IndoorMap

Doors: wide, compact.

States: default.

Events: `map.select(room)`.

| Prop | Type | Notes |
|---|---|---|
| `liveLayers` | array | [{label, value, source}] |
| `path` | array | [] |
| `plan` | id | venue asset |
| `rooms` | array | [] |
| `you` | object | position |

## LocationShare

Doors: wide, compact.

States: off, sharing, expired.

Events: `location.share`, `location.stop`.

| Prop | Type | Notes |
|---|---|---|
| `audience` | scope | scope |
| `precision` | enum | exact\|~500 m\|place-only\|off |
| `until` | enum | task end\|time\|arrival |

## MapView

Doors: wide, compact.

States: loading, ready, no-location.

Events: `map.select(point)`, `map.area(polygon)`.

| Prop | Type | Notes |
|---|---|---|
| `areas` | array | [{polygon, label}] |
| `points` | array | [{id, label, kind, lat, lng, ref?}] |
| `routes` | array | [{path, mode, eta}] |
| `selected` | id | id? |
| `you` | object | {position, precision} |

## PlacePicker

Doors: wide, compact.

States: searching, results, pinned.

Events: `place.pick(ref)`, `place.adjust(ref, x, y)`.

| Prop | Type | Notes |
|---|---|---|
| `pin` | object | position |
| `query` | string | string |
| `results` | array | [{place, distance, facts[], limitCheck}] |

## RouteCard

Doors: wide, compact, lens.

States: planned, moving, arrived.

| Prop | Type | Notes |
|---|---|---|
| `distance` | number | metres, bound to its source |
| `eta` | datetime | ISO |
| `mode` | string | string |
| `participants` | array | [participant] |
| `progress` | number | 0-1 |
| `steps` | array | [{label, state, time}] |
| `costPerMember` | number | Estimated cost per member in the supplied currency; bound to its source event. |
| `currency` | string | ISO 4217 currency code for the estimated per-member cost. |

## TimeZoneStrip

Doors: wide, compact.

States: default.

| Prop | Type | Notes |
|---|---|---|
| `now` | datetime | ISO |
| `people` | array | [{participant, tz, workingHours (ranges)}] |
