# Conversation and calls

<!-- Written by tools/gen_docs.py. Edit the source, then run it again. -->

16 components in the `coalitionkit/v0_9` catalog.

## AgentHandoff

Doors: wide, compact, message, voice.

States: open, answered.

Events: `handoff.answer(value)`.

| Prop | Type | Notes |
|---|---|---|
| `choices` | array | [] |
| `question` | string | string |
| `reason` | string | string |
| `rule` | string | string |

## AgentStatus

Doors: wide, compact, lens.

States: listening, answering, needs-you, paused, offline.

Events: `agent.pause`, `agent.resume`.

| Prop | Type | Notes |
|---|---|---|
| `budget` | object | {used, cap} |
| `state` | enum | listening\|answering\|needs-you\|paused\|offline |
| `task` | id | ref? |

## AskAgent

Doors: wide, compact.

States: draft, asked, answered.

Events: `coalition.query`.

| Prop | Type | Notes |
|---|---|---|
| `kind` | enum | bool\|number-range\|choice |
| `task_id` | id | ref |
| `text` | string | string |
| `to` | id | participant |

## CallInvite

Doors: wide, compact, lens.

States: ringing, missed.

Events: `call.join`, `call.join_muted`, `call.decline`.

| Prop | Type | Notes |
|---|---|---|
| `caller` | id | participant |
| `consents` | array | [{kind, default off}] |
| `listeners` | array | [agent] |
| `title` | string | string |

## CallSummary

Doors: wide, compact.

States: draft, posted.

Events: `summary.post(item)`, `transcript.open(id)`.

| Prop | Type | Notes |
|---|---|---|
| `decided` | array | [] |
| `duration` | number | s |
| `needs` | array | [] |
| `offers` | array | [] |
| `questions` | array | [] |
| `participants` | string | Participant count summary. |
| `transcript` | id | Transcript reference for opening the viewer projection. |

## ChannelDigest

Doors: message.

States: sent.

| Prop | Type | Notes |
|---|---|---|
| `channel` | enum | email\|sms |
| `items` | array | [{tone, text, ref}] |
| `period` | string | string |

## CoalitionThread

Doors: wide, compact.

States: empty, streaming, typing, system-row.

Events: `message.open(id)`.

| Prop | Type | Notes |
|---|---|---|
| `messages` | array | [{author: person\|agent\|host\|steward, text, attachments[], card?, scope, time}] |
| `typing` | array | [participant] |

## Composer

Doors: wide, compact.

States: empty, typing, mention-menu, command-menu, recording.

Events: `message.send(text, scope)`, `need.publish`, `offer.publish`, `voice.record`.

| Prop | Type | Notes |
|---|---|---|
| `initialText` | string | Initial editable message text, including mention or slash prefix. |
| `initialRecording` | boolean | Initially show a voice recording; does not start microphone capture. |
| `initialElapsed` | number | Initial recording duration in seconds, with event provenance. |
| `attachments` | array | → vault |
| `audience` | scope | scope (narrowest default) |
| `commands` | array | /need\|/offer\|/ask\|/private |
| `mentions` | array | [participant] |

## DiarizedTranscript

Doors: wide, compact.

States: live, final.

Events: `extract.review`, `extract.post(id) → speaker-signed`.

| Prop | Type | Notes |
|---|---|---|
| `extracted` | array | [{kind: need\|offer\|decision, text, segment}] |
| `segments` | array | [{speaker, start, text, confidence}] |

## ElicitationForm

Doors: mcp-app.

States: asked, re-asked on change, answered.

Events: `elicitation.accept`, `elicitation.decline`, `elicitation.cancel`.

| Prop | Type | Notes |
|---|---|---|
| `binding` | object | bearer + subject revision |
| `decision_deadline` | datetime | ISO 8601; after it the decision is closed (deadline_exceeded) |
| `message` | string | stable text |
| `schema` | object | ConsentAnswer {yes} |
| `subject` | subject | {kind, id, revision}: the revision-bound subject of the decision |

## McpAppView

Doors: mcp-app.

States: loading, ready.

Events: `tool: my_view, decide, ...`.

| Prop | Type | Notes |
|---|---|---|
| `resourceUri` | string | ui://coalitionkit/surface-v1.html |
| `tree` | children | A2UI (viewer) |

## Message

Doors: wide, compact, message.

States: sending, delivered, seen, failed, redacted, blocked.

Events: `message.retry`.

| Prop | Type | Notes |
|---|---|---|
| `policy` | id | id? |
| `redactions` | array | [path] |
| `state` | enum | sending\|delivered\|seen\|failed\|redacted\|blocked |
| `text` | string | string |
| `seen_count` | number | Number of viewers who have seen the message. |
| `projection` | array | Viewer-safe text and redaction length spans; never contains hidden text. |
| `scope` | string | Scope caption for the viewer projection. |

## NegotiationTheatre

Doors: wide.

States: live, replay.

Events: `turn.inspect(event_ref)`.

| Prop | Type | Notes |
|---|---|---|
| `events` | array | viewer projection [] |
| `speakers` | array | seats |

## ToolCall

Doors: wide, compact.

States: running, done, failed.

Events: `toolcall.expand`.

| Prop | Type | Notes |
|---|---|---|
| `args` | object | viewer projection |
| `state` | enum | running\|done\|failed |
| `summary` | string | string |
| `tool` | string | name |
| `duration` | number | Elapsed call time in seconds. |
| `failure` | string | Safe failure reason. |
| `provenance` | string | Viewer-safe result provenance caption. |
| `emphasis` | string | Leading summary text to emphasize. |

## VideoCall

Doors: wide.

States: connecting, live, reconnecting, ended.

Events: `call.mute`, `call.camera`, `call.share`, `call.end`, `call.captions`.

| Prop | Type | Notes |
|---|---|---|
| `captions` | boolean | bool |
| `recording` | enum | transcript\|off |
| `tiles` | array | [{participant, kind: person\|agent\|screen, speaking, muted}] |
| `title` | string | Call title. |
| `elapsed` | string | Formatted elapsed call time. |

## VoiceCall

Doors: compact.

States: ringing, live, ended.

Events: `call.mute`, `call.speaker`, `call.end`.

| Prop | Type | Notes |
|---|---|---|
| `caption` | string | string |
| `participants` | array | [] |
| `speaking` | id | participant |
| `title` | string | Call title. |
| `elapsed` | string | Formatted elapsed call time. |
| `clock` | string | Device time label. |
