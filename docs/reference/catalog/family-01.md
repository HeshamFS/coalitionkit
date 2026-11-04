# Foundations

<!-- Written by tools/gen_docs.py. Edit the source, then run it again. -->

58 components in the `coalitionkit/v0_9` catalog.

## AudioPlayer

Doors: wide, compact, message, voice.

States: paused, playing.

Events: `media.play`, `media.pause`, `media.seek(t)`.

| Prop | Type | Notes |
|---|---|---|
| `src` | binding | path |
| `title` | string | string? |
| `duration` | number | Bound media duration in seconds. |
| `elapsed` | number | Bound initial playback position in seconds. |
| `waveform` | array | Bound amplitude samples for the voice waveform, from zero to one. |
| `transcript` | binding | Plain-text transcript from the host. |

## Avatar

Doors: wide, compact, lens, message.

States: default, speaking.

| Prop | Type | Notes |
|---|---|---|
| `label` | string | string |
| `presence` | enum | live\|away\|off |
| `ring` | boolean | bool |
| `seat` | enum | 1-5\|host\|steward |
| `size` | enum | xs\|sm\|lg\|xl |

## AvatarStack

Doors: wide, compact.

States: default.

| Prop | Type | Notes |
|---|---|---|
| `max` | number | int |
| `people` | array | [participant] |

## Badge

Doors: wide, compact, lens, message, voice.

States: default.

| Prop | Type | Notes |
|---|---|---|
| `kind` | enum | measured \| vault \| signed \| model \| estimate \| example |
| `label` | string | string |

## Banner

Doors: wide, compact, message.

States: shown.

Events: `banner.action`, `banner.dismiss`.

| Prop | Type | Notes |
|---|---|---|
| `action` | object | ? |
| `body` | string | string |
| `title` | string | string |
| `tone` | enum | info\|ask\|blocked\|agreed |

## Button

Doors: wide, compact, lens, message, voice.

States: default, hover, focus, disabled, busy.

Events: `action.name(context)`.

| Prop | Type | Notes |
|---|---|---|
| `action` | object | {name,context} |
| `busy` | boolean | boolean? |
| `disabled` | boolean | boolean? |
| `label` | string | string |
| `size` | enum | sm \| md \| lg |
| `variant` | enum | primary \| secondary \| ink \| ghost |
| `tone` | enum | Optional soft or destructive treatment shown by the control sheet. |
| `icon` | string | Optional leading icon name. |
| `trailingIcon` | string | Optional trailing icon name. |

## ButtonGroup

Doors: wide, compact, lens.

States: default.

Events: `action.name(context)`.

| Prop | Type | Notes |
|---|---|---|
| `children` | children | Button[] |

## Card

Doors: wide, compact, lens.

States: default, live, ask.

Events: `open(subject)`.

| Prop | Type | Notes |
|---|---|---|
| `children` | children | id[] |
| `fields` | array | [{label, value, provenance}] |
| `provenance` | enum |  |
| `scope` | scope | Scope? |
| `status` | enum |  |
| `title` | string | string? |
| `tone` | enum | default \| live \| ask \| dashed |

## CheckBox

Doors: wide, compact, message, voice.

States: off, on, disabled.

Events: `change(value)`.

| Prop | Type | Notes |
|---|---|---|
| `label` | string | string |
| `value` | binding | path |
| `description` | string | Supporting description beneath the label. |
| `disabled` | boolean | Disable changes to the value. |

## Chip

Doors: wide, compact, lens, message, voice.

States: default, selected.

Events: `select(id)`.

| Prop | Type | Notes |
|---|---|---|
| `label` | string | string |
| `seat` | string | 1..5? |
| `selected` | boolean | boolean? |
| `disabled` | boolean | Disabled chip. |
| `dashed` | boolean | Dashed add-item treatment. |

## ChoicePicker

Doors: wide, compact, message, voice.

States: none, one, many.

Events: `select(value)`.

| Prop | Type | Notes |
|---|---|---|
| `display` | enum | chips \| menu |
| `multiple` | boolean | boolean? |
| `options` | array | {id,label}[] |
| `value` | binding | path |

## Column

Doors: wide, compact, lens, message, voice.

States: default.

| Prop | Type | Notes |
|---|---|---|
| `children` | children | id[] |
| `gap` | enum | 4 \| 8 \| 12 \| 16 |
| `spacing` | number | Optional bound spacing in pixels, overriding the gap preset for tightly grouped content. |

## CommandPalette

Doors: wide.

States: open, results, empty.

Events: `command.run(id)`, `command.ask(text)`.

| Prop | Type | Notes |
|---|---|---|
| `groups` | enum | actions\|objects\|log\|ask |
| `query` | binding | path |

## DateTimeInput

Doors: wide, compact, message, voice.

States: empty, filled, error.

Events: `change(value)`.

| Prop | Type | Notes |
|---|---|---|
| `mode` | enum | date \| time \| datetime |
| `tz` | string | host-supplied |
| `value` | binding | path |
| `range` | boolean | Select a start and end date from the calendar. |
| `busy` | array | Unavailable ISO dates from the private calendar match, without names. |
| `min` | datetime | Earliest selectable date. |
| `max` | datetime | Latest selectable date. |

## Deadline

Doors: wide, compact, lens, message, voice.

States: calm, ask, passed.

| Prop | Type | Notes |
|---|---|---|
| `consequence` | string | string |
| `deadline` | datetime | ISO |
| `label` | string | string |
| `startedAt` | datetime | Start of the decision window, used for elapsed progress. |

## Divider

Doors: wide, compact, lens, message, voice.

States: default.

| Prop | Type | Notes |
|---|---|---|
| `label` | string | Optional text between the dividing rules. |

## Drawer

Doors: wide.

States: open.

Events: `drawer.close`.

| Prop | Type | Notes |
|---|---|---|
| `body` | children | components |
| `footer` | children | actions |
| `side` | enum | right\|left |
| `title` | string | string |
| `width` | number | 360-480 |

## EmptyState

Doors: wide, compact.

States: default.

Events: `action.invoke`.

| Prop | Type | Notes |
|---|---|---|
| `action` | object | ? |
| `body` | string | who fills it |
| `glyph` | string | icon |
| `title` | string | string |

## ErrorState

Doors: wide, compact.

States: error, reconnecting.

Events: `error.retry`.

| Prop | Type | Notes |
|---|---|---|
| `cause` | string | plain words |
| `details` | object | {code, ref} |
| `lastSeen` | datetime | ISO? |
| `retry` | boolean | bool |
| `missedEvents` | number | Bound count of missed events that will replay during reconnection. |

## FileDrop

Doors: wide, compact.

States: idle, dragover, uploading, error.

Events: `file.add(file)`.

| Prop | Type | Notes |
|---|---|---|
| `accept` | array | mime[] |
| `maxBytes` | number | number |
| `target` | binding | path |

## FilterBar

Doors: wide, compact.

States: default, filtered.

Events: `filter.change`, `sort.change`.

| Prop | Type | Notes |
|---|---|---|
| `filters` | array | [{field, op, value}] |
| `groupBy` | string | field? |
| `query` | binding | path |
| `resultCount` | binding | path |
| `sort` | object | {field, dir} |
| `options` | array | Available filter groups {field, label, options: [{value, label}]}. |
| `placeholder` | string | Search input placeholder. |
| `resultLabel` | string | Host-provided summary of the current result count and matches. |

## Grid

Doors: wide, compact, lens, message, voice.

States: default.

| Prop | Type | Notes |
|---|---|---|
| `children` | children | id[] |
| `columns` | number | 1..4 |
| `fields` | array | [{label, value, provenance}] |
| `gap` | enum | 4 \| 8 \| 12 \| 16 |
| `provenance` | enum |  |
| `status` | enum |  |

## Heading

Doors: wide, compact, lens, message, voice.

States: default.

| Prop | Type | Notes |
|---|---|---|
| `text` | string | path \| literal |
| `tone` | enum | default \| blue |
| `variant` | enum | h1 \| h2 \| h3 |

## Icon

Doors: wide, compact, lens.

States: default.

| Prop | Type | Notes |
|---|---|---|
| `label` | string | string? |
| `name` | string | closed icon set |
| `size` | enum | 16 \| 20 \| 24 |
| `tone` | enum | ink \| blue |

## IconButton

Doors: wide, compact, lens.

States: default, hover, focus, disabled.

Events: `action.name(context)`.

| Prop | Type | Notes |
|---|---|---|
| `action` | object | {name,context} |
| `ariaLabel` | string | string (required) |
| `icon` | string | name |

## Image

Doors: wide, compact, message.

States: loading, loaded, failed.

| Prop | Type | Notes |
|---|---|---|
| `alt` | string | string (required) |
| `evidence` | id | id? |
| `src` | binding | path |

## KeyValue

Doors: wide, compact, lens, message, voice.

States: default.

| Prop | Type | Notes |
|---|---|---|
| `pairs` | array | {label,value:path,provenance?:id,scope?:Scope}[] |

## Link

Doors: wide, compact, message.

States: default, hover, focus, visited.

Events: `link.open(href)`.

| Prop | Type | Notes |
|---|---|---|
| `href` | string | path \| https literal |
| `text` | string | string |

## List

Doors: wide, compact, lens, message, voice.

States: empty, filled.

Events: `open(item)`, `select(item)`.

| Prop | Type | Notes |
|---|---|---|
| `empty` | string | string? |
| `items` | binding | path |
| `max` | number | number? |
| `selectable` | boolean | boolean? |
| `template` | string | id |

## Menu

Doors: wide, compact.

States: open, item-hover, submenu.

Events: `menu.pick(id)`.

| Prop | Type | Notes |
|---|---|---|
| `items` | array | [{label, icon?, shortcut?, submenu?, tone, disabled?}] |

## Meter

Doors: wide, compact, lens, voice.

States: ok, warn, bad.

| Prop | Type | Notes |
|---|---|---|
| `bands` | array | {upTo,tone}[] |
| `label` | string | string |
| `max` | number |  |
| `min` | number |  |
| `provenance` | enum | id |
| `unit` | string |  |
| `value` | number | path |
| `caption` | string | Secondary measurement caption below the label. |

## Modal

Doors: wide.

States: closed, open.

Events: `dismiss`.

| Prop | Type | Notes |
|---|---|---|
| `children` | children | id[] |
| `dismissible` | boolean | boolean |
| `open` | binding | path |
| `title` | string | string |

## NumberField

Doors: wide, compact, message, voice.

States: empty, filled, focus, error.

Events: `change(value, unit)`.

| Prop | Type | Notes |
|---|---|---|
| `label` | string | string |
| `max` | number | number? |
| `min` | number | number? |
| `step` | number | number? |
| `unit` | string | string |
| `value` | binding | path |
| `currency` | string | Currency prefix before the number. |
| `help` | string | Supporting text beneath the numeric input. |

## Panel

Doors: wide, compact, lens.

States: default.

| Prop | Type | Notes |
|---|---|---|
| `children` | children | id[] |
| `fields` | array | [{label, value, provenance}] |
| `provenance` | enum |  |
| `scope` | scope | Scope? |
| `status` | enum |  |
| `title` | string | string? |

## Popover

Doors: wide.

States: open.

Events: `popover.close`.

| Prop | Type | Notes |
|---|---|---|
| `actions` | number | ≤2 |
| `anchor` | id | id |
| `body` | children | components |
| `title` | string | string |

## Progress

Doors: wide, compact, lens, voice.

States: determinate, stepped, indeterminate.

| Prop | Type | Notes |
|---|---|---|
| `label` | string | string |
| `max` | number |  |
| `min` | number |  |
| `provenance` | enum | id |
| `steps` | number | number? |
| `unit` | string |  |
| `value` | number | path (0..1) |
| `stepLabels` | array | Ordered labels for a numbered workflow; value is the active step. |

## RadioGroup

Doors: wide, compact, message, voice.

States: none, selected.

Events: `change(value)`.

| Prop | Type | Notes |
|---|---|---|
| `options` | array | {id,label}[] |
| `value` | binding | path |

## RichText

Doors: wide, compact, message, voice.

States: default.

Events: `link.open(href)`.

| Prop | Type | Notes |
|---|---|---|
| `allow` | enum | bold \| italic \| list \| link |
| `markdown` | string | path \| literal |

## Row

Doors: wide, compact, lens, message, voice.

States: default.

| Prop | Type | Notes |
|---|---|---|
| `align` | enum | start \| center \| end |
| `children` | children | id[] |
| `gap` | enum | 4 \| 8 \| 12 \| 16 |

## SearchField

Doors: wide, compact.

States: empty, typing, results, no-results.

Events: `search.change(q)`, `search.pick(id)`.

| Prop | Type | Notes |
|---|---|---|
| `groups` | array | [{label, items[]}] |
| `query` | binding | path |

## SegmentedControl

Doors: wide, compact, message.

States: pressed, unpressed.

Events: `select(value)`.

| Prop | Type | Notes |
|---|---|---|
| `options` | array | {id,label}[] |
| `value` | binding | path |

## Sheet

Doors: compact.

States: closed, open.

Events: `dismiss`.

| Prop | Type | Notes |
|---|---|---|
| `children` | children | id[] |
| `dismissible` | boolean | boolean |
| `open` | binding | path |
| `title` | string | string |

## Skeleton

Doors: wide, compact.

States: skeleton, filled, live, rest, changed.

| Prop | Type | Notes |
|---|---|---|
| `lines` | number | number? |
| `previous` | binding | path? |
| `provenance` | enum | id? |
| `reserves` | number | px |
| `shape` | enum | line \| block \| avatar \| card |
| `state` | enum | skeleton \| filled \| live \| rest \| changed |

## Slider

Doors: wide, compact.

States: default, focus, disabled.

Events: `change(value)`.

| Prop | Type | Notes |
|---|---|---|
| `max` | number | number |
| `min` | number | number |
| `step` | number | number |
| `unit` | string | string? |
| `value` | binding | path |
| `marks` | array | Tick marks {at: bound number, label, tone?}. |
| `format` | enum | Format numeric values as numbers or minutes since midnight. |
| `valueLabel` | string | Optional output caption, such as the participant floor. |

## SlotPicker

Doors: wide, compact.

States: loading, ready, held, none-shared.

Events: `slot.hold(start)`, `slot.release(start)`.

| Prop | Type | Notes |
|---|---|---|
| `days` | array | [{date, slots[{start, state: free\|mine\|shared\|off}]}] |
| `duration` | number | minutes |
| `selected` | datetime | start? |
| `source` | string | psi_match |
| `participants` | number | Bound participant count from the private calendar match. |

## Spinner

Doors: wide, compact, lens.

States: spinning.

| Prop | Type | Notes |
|---|---|---|
| `label` | string | string? |

## SplitButton

Doors: wide, compact.

States: closed, open.

Events: `action.invoke(value)`.

| Prop | Type | Notes |
|---|---|---|
| `items` | array | [{label, value, hint?, disabled?}] |
| `primary` | string | value |

## Switch

Doors: wide, compact.

States: off, on, disabled.

Events: `change(value)`.

| Prop | Type | Notes |
|---|---|---|
| `label` | string | string |
| `value` | binding | path |
| `description` | string | Supporting description beneath the label. |
| `disabled` | boolean | Disable changes to the value. |

## Table

Doors: wide, compact, message, voice.

States: empty, filled.

Events: `sort(key)`, `open(row)`, `table.action(ids)`, `table.page(page)`, `select(ids)`.

| Prop | Type | Notes |
|---|---|---|
| `columns` | array | {key,label,align?,unit?}[] |
| `rows` | binding | path |
| `sortable` | boolean | boolean? |
| `selection` | enum | Row selection mode. |
| `selected` | array | Selected row identifiers. |
| `total` | number | Bound total result count from the host. |
| `page` | number | Bound current page, starting at one. |
| `pageSize` | number | Bound maximum rows per page. |
| `action` | object | Optional bulk action {label}; invokes table.action with selected identifiers. |

## Tabs

Doors: wide, compact, message.

States: selected, unselected.

Events: `select(value)`.

| Prop | Type | Notes |
|---|---|---|
| `options` | array | {id,label}[] |
| `panels` | children | id[] |
| `value` | binding | path |

## Tag

Doors: wide, compact, lens, message, voice.

States: agreed, needs, changed, private, blocked.

| Prop | Type | Notes |
|---|---|---|
| `kind` | enum | agreed \| needs \| changed \| private \| blocked |
| `label` | string | string |

## Text

Doors: wide, compact, lens, message, voice.

States: default.

| Prop | Type | Notes |
|---|---|---|
| `provenance` | enum | id? |
| `text` | string | path \| literal |
| `tone` | enum | default \| muted \| blue |
| `variant` | enum | body \| caption |

## TextArea

Doors: wide, compact, message, voice.

States: empty, filled, focus, error, disabled.

Events: `change(value)`.

| Prop | Type | Notes |
|---|---|---|
| `error` | binding | path? |
| `label` | string | string |
| `maxLength` | number | number? |
| `value` | binding | path |
| `decorations` | array | Plain-text decorations {text, kind: bold \| mention}; editing remains plain text. |
| `placeholder` | string | Placeholder while the text area is empty. |

## TextField

Doors: wide, compact, message, voice.

States: empty, filled, focus, error, disabled.

Events: `change(value)`, `submit(value)`.

| Prop | Type | Notes |
|---|---|---|
| `error` | binding | path? |
| `label` | string | string |
| `maxLength` | number | number? |
| `placeholder` | string | string? |
| `value` | binding | path |
| `help` | string | Supporting text beneath the input. |
| `readOnly` | boolean | Read-only input. |
| `private` | boolean | Display a vault placeholder instead of the bound value. |

## TimeZone

Doors: wide, compact.

States: default.

Events: `tz.change`.

| Prop | Type | Notes |
|---|---|---|
| `others` | array | [{participant, tz}] |
| `value` | string | IANA tz |
| `at` | datetime | Instant shown in each participant time zone. |
| `label` | string | Viewer time-zone display label. |

## Toast

Doors: wide, compact, lens.

States: shown, stacked, dismissed.

Events: `toast.action`, `toast.undo`.

| Prop | Type | Notes |
|---|---|---|
| `action` | object | ? |
| `text` | string | ≤60 |
| `tone` | enum | done\|change\|error |
| `undoWindow` | number | s |

## Tooltip

Doors: wide.

States: hidden, shown.

| Prop | Type | Notes |
|---|---|---|
| `target` | id | id |
| `tip` | string | string |
| `shortcut` | string | Optional keyboard shortcut displayed in the tooltip. |

## Video

Doors: wide, compact.

States: paused, playing.

Events: `media.play`, `media.pause`, `media.seek(t)`.

| Prop | Type | Notes |
|---|---|---|
| `captions` | binding | path? |
| `poster` | binding | path? |
| `src` | binding | path |
| `duration` | number | Bound media duration in seconds. |
| `elapsed` | number | Bound initial playback position in seconds. |
| `caption` | string | Current plain-text caption supplied by the host. |
