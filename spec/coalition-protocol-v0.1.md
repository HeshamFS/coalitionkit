# Coalition Protocol v0.1 (draft)

## Status, conformance language and versioning

This is a working draft of Coalition Protocol v0.1, an extension to A2A for sessions shared by many agents. It will change in response to implementers until v1.0 declares it stable.

- **Status**: draft, October 2026. Published with the reference implementation under Apache 2.0.
- **Conformance language**: MUST, MUST NOT, SHOULD, SHOULD NOT and MAY are used as in RFC 2119 and RFC 8174.
- **Versioning**: the extension URI carries the major version (`/coalition/v0`). Minor versions only add optional fields and message types; anything that breaks a v0 implementation gets a new URI. Every envelope carries `ext_version`.
- **Normative dependencies**: A2A protocol 1.0 (bug-fix release 1.0.1); JSON Schema 2020-12; JWS (RFC 7515), JWK for Ed25519 (RFC 8037) and JSON Canonicalization Scheme (RFC 8785) for signatures; RFC 3339 timestamps; ULIDs for identifiers; ristretto255 (RFC 9496) and RFC 9380 for PSI.
- **Fixed identifiers**: the extension URI is `https://coalitionkit.dev/ext/coalition/v0`; every schema `$id` starts with `https://coalitionkit.dev/schemas/coalition/v0/`.

**Roles**

| Role | Who plays it | Must implement |
|---|---|---|
| Host | The runtime running a Coalition (Coalition Host and Gardener) | Ordering, lifecycle, scopes, authorization, projections, receipts, the Steward hook |
| Member | Any participant's agent | Joining, offers, decisions, commitments, scope handling |
| Owner | The person or organization a member speaks for, holding an owner key | Consent: signing every decision |
| Vault | The private store behind a member | Typed answers and the PSI exchange |
| Steward | The independent checker | Verdicts on messages, plans and minted artifacts |
| Edge | An adapter that turns outside input into observations | Observation messages with sources |

**Three keys, three jobs.** The *agent key* is the key of the member's signed card; it signs the member's envelopes. The *owner key* (Ed25519) is bound to the participant at join and signs consent; the agent key can never stand in for it. The *host key* is the key of the host's signed card, pinned by every member; it signs everything the host originates, every projection and every receipt.

## Binding to A2A

The Coalition Protocol adds no transport of its own: a Coalition is a set of A2A tasks that share one `contextId`, and every Coalition message travels as a data part inside an A2A message.

**Extension URI**: `https://coalitionkit.dev/ext/coalition/v0`. Every call carries the `A2A-Version: 1.0` header; a host treats a call without it as A2A 0.3 and refuses it.

**Declaring support.** A conforming agent lists the extension in its Agent Card under `capabilities.extensions`, using A2A's `AgentExtension` fields (`uri`, `description`, `required`, `params`):

```json
{
  "capabilities": {
    "streaming": true,
    "extensions": [{
      "uri": "https://coalitionkit.dev/ext/coalition/v0",
      "description": "Takes part in multi-party Coalitions",
      "required": false,
      "params": {
        "roles": ["member"],
        "vault": "local",
        "psi": { "scheme": "ecdh-ristretto255", "library": "coalitionkit.psi" },
        "surfaces": ["web", "mcp_app"]
      }
    }]
  }
}
```

**Signed cards.** Every card used in a Coalition MUST carry at least one entry in A2A's `signatures` list: a JWS whose protected header names `alg`, `typ` (`JOSE`) and `kid`, over the card canonicalized with JCS after removing the `signatures` field and every field left at its default value. The card lists its endpoints in `supportedInterfaces` (binding `JSONRPC`, version `1.0`). A card is untrusted until verified: the host pins the key it verified at join, never follows a `jku` URL from the card, and MUST reject unsigned cards, expired or revoked keys, and cards whose owner proof it cannot verify. Members pin the host's card key the same way, from the invitation they joined by.

**Mapping**

| Coalition concept | A2A construct |
|---|---|
| Coalition | A shared `contextId` equal to the Coalition ID |
| Exchange | One A2A task per exchange on the member's agent. The member's server assigns task IDs; once a task reaches a final state, the host starts a new task in the same `contextId` |
| Host to member | Messages and streamed task updates on that task |
| Member to host | Messages sent to the host's own A2A endpoint, which has its own signed card |
| Coalition message | A Part whose `data` is the envelope, with media type `application/vnd.coalitionkit.envelope+json`; the message's `extensions` list names the extension URI |
| Acknowledgement | Two such parts, in order: the accepted event in the form the sender may see (original or projection), then its `coalition.receipt`; only the receipt when the sender is outside the event's scope |
| Input from a person | The member's task waits in `TASK_STATE_INPUT_REQUIRED`; the answer continues it with the same task and context IDs |
| Coalition end | Open member tasks move to a final state when the Coalition dissolves |

Members MUST activate the extension on each call with the `A2A-Extensions` header carrying the extension URI (not `X-A2A-Extensions`, which some SDK docs still show), and the host MUST ignore Coalition data parts on calls that did not activate it. The extension is declared with `required: false`, so an agent without it can still reach the host's other skills.

## The message envelope

Every Coalition message is one envelope. The sender fills and signs the envelope without `seq`, `ts` and `prev_hash`; the host assigns those three when it accepts the message. The host takes the sender from the authenticated connection and refuses an envelope whose `sender` or `on_behalf_of` differs from it. Envelopes the host itself originates (`charter`, `need`, `query`, `propose`, `tension`, `dissolve`, `error`, `projection`, `receipt`) carry the host's card URL as `sender`, the literal `host` as `on_behalf_of`, and are signed with the host key.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://coalitionkit.dev/schemas/coalition/v0/envelope.json",
  "type": "object",
  "additionalProperties": false,
  "required": ["ext_version", "coalition_id", "event_id", "type", "sender", "on_behalf_of", "scope", "payload", "sig"],
  "properties": {
    "ext_version": { "const": "0.1" },
    "coalition_id": { "type": "string", "pattern": "^[0-9A-HJKMNP-TV-Z]{26}$" },
    "event_id": { "type": "string", "pattern": "^[0-9A-HJKMNP-TV-Z]{26}$" },
    "type": { "type": "string", "pattern": "^coalition\\.[a-z_]+$" },
    "sender": { "type": "string", "format": "uri", "description": "URL of the sender's signed Agent Card" },
    "on_behalf_of": { "type": "string", "description": "Participant ID of the owner the sender speaks for" },
    "scope": { "$ref": "scope.json" },
    "causation_id": { "type": "string", "pattern": "^[0-9A-HJKMNP-TV-Z]{26}$" },
    "correlation_id": { "type": "string", "pattern": "^[0-9A-HJKMNP-TV-Z]{26}$" },
    "payload": { "type": "object", "description": "Validated against the schema for this type" },
    "sig": { "type": "string", "description": "Compact JWS (detached payload) over the JCS-canonical envelope without sig, seq, ts and prev_hash" },
    "seq": { "type": "integer", "minimum": 1, "description": "Set by the host" },
    "ts": { "type": "string", "format": "date-time", "description": "Set by the host: when it accepted the envelope" },
    "prev_hash": { "type": "string", "pattern": "^[a-f0-9]{64}$", "description": "Set by the host" }
  }
}
```

**Signature form.** `sig` is a compact JWS with a detached payload, `<protected>..<signature>`; the protected header holds exactly `alg: EdDSA`, `typ: JOSE` and `kid`. The verifier rebuilds the payload as the JCS form of the envelope without `sig`, `seq`, `ts` and `prev_hash`. Every other signature in this document (`consent_sig`, `owner_proof`) has the same form over its own JCS payload.

**Rules**

- The log keeps every original signed envelope exactly as the sender signed it, plus the host fields. The log is the only source of truth; anything else the host delivers is derived from it (see Projections).
- `seq` comes from a per-Coalition counter row incremented in the same transaction as the append, so the log has no gaps; a database sequence would leave gaps on rollback.
- `prev_hash` is the SHA-256 of the JCS form of the previous accepted envelope in the same Coalition (all fields, `sig` included), so any gap or edit in the log is detectable. The `prev_hash` of seq 1 is the genesis hash (see The authenticated log boundary).
- An event is committed to the log before it is delivered, projected or answered; nobody sees a change the log cannot rebuild.
- Signatures and hashes are computed over JCS (RFC 8785), so a number re-encoded on the way (200 as 200.0) still verifies. Every integer in a payload lies between 0 and 2^53 - 1, which is what JCS can carry exactly. Money is an integer in minor units (cents), never a float.
- Every payload schema sets `additionalProperties: false`. A member therefore cannot attach extra fields, such as reasons, that the protocol does not define.
- Object identifiers the host mints (needs, tasks, plans, tensions) are ULIDs. A member mints the ULID of each commitment it creates, in its signed `commit`; the host rejects a `commitment_id` already used in the Coalition, in any state, with `not_authorized`. Identifiers a participant mints (`offer_id`, `query_id` answered by it, `match_id`) are strings of 1 to 128 characters.

### Idempotency is authenticated

The host looks up every submission by (`coalition_id`, `event_id`) before it does anything else that depends on the content. It then compares the authenticated sender and the *submission digest*, the SHA-256 of the JCS form of the resubmitted envelope without its host fields (`seq`, `ts`, `prev_hash`; `sig` stays in):

| Lookup finds | Same authenticated sender and same digest | Result |
|---|---|---|
| Nothing | n/a | Process normally |
| An accepted event | Yes | Return the acknowledgement again, in the form the sender may see (see Acknowledgements and receipts); append nothing |
| An accepted event | No (other sender, or other bytes) | Reject with `duplicate_mismatch` |

`duplicate_mismatch` discloses nothing about the original: the same answer, with an empty `detail`, whichever of the two differed and whether or not the sender could ever see the original. A sender that really wants to change a message sends it under a new `event_id`.

### Acknowledgements and receipts

The host acknowledges every accepted envelope with the accepted envelope (now carrying `seq`, `ts` and `prev_hash`) and a host-signed `coalition.receipt` with payload `{coalition_id, seq, head_hash}`, where `head_hash` is the SHA-256 of the JCS form of the accepted envelope at `seq`, which is also the value the next envelope's `prev_hash` must hold. A receipt is scoped to its recipient, signed with the host key and never appended to the log. The sender SHOULD keep every receipt. A host MUST NOT acknowledge an event it has not committed.

**The acknowledgement obeys scope.** The first part of an acknowledgement is the event as the sender would receive it as any recipient, by the delivery form rule under Projections: the *original* when the sender is in the event's scope and nothing is redacted or viewer-specific for it; a *projection* when the sender is in scope and a field is redacted or the event is viewer-specific; and *nothing* (the receipt alone) when the sender is outside the event's scope. A duplicate gets the same form, computed again from the stored event, and the same receipt. The receipt carries only `seq` and `head_hash`, which disclose nothing of the content.

### The authenticated log boundary

The genesis: `prev_hash` of seq 1 is the SHA-256 (lowercase hex) of the JCS form of `{"coalition_id", "host_card_url", "created_at"}`, where `host_card_url` is the host's card URL and `created_at` is the RFC 3339 time the host created the Coalition. `created_at` is also carried in every `coalition.charter`, so a member can recompute the genesis hash.

A reader that holds the whole log, or a replay in which events outside its scope are replaced by stubs `{seq, prev_hash, hash}` (the stub's `hash` being the SHA-256 of the JCS form of the original), checks four things: seq is gap-free from 1; seq 1 links to the genesis hash; each `prev_hash` equals the hash of the entry before it; and, for every receipt it kept, the log reaches that receipt's `seq` and the entry there hashes to the receipt's `head_hash`. A projection stands in for its source entry through the stub it carries (see Projections): the reader MUST verify the projection's host signature against the pinned host key first, and a projection that fails is an error, not a gap; only then do the chain and receipt checks use its `source.prev_hash` and `source.hash`, never a hash of the projection's own envelope. In `coalitionkit_contracts`, `verify_chain` and `check_receipts` take the host key and verify each projection before it enters the chain. The first three catch gaps and edits inside the log. Only the receipts catch an edited last entry, an edited tail whose later `prev_hash` values were recomputed, and a truncation: a host that cuts the log back, or rewrites its tail, cannot produce a log that fits a receipt it signed earlier. A member can detect only what its own receipts cover.

### Projections

Anything delivered with a field redacted, or projected for a particular viewer, is a *projection*: an envelope of type `coalition.projection` signed by the host key. It never carries the sender's original JWS and is never appended to the log. Its payload is:

| Field | Meaning |
|---|---|
| `source` | `event_id`, `seq`, `type` and `on_behalf_of` of the logged event it is derived from, plus `prev_hash` (its `prev_hash`) and `hash` (the SHA-256 of the JCS form of the original entry, the value the next entry's `prev_hash` holds). Signed with the projection, these are the stub `{seq, prev_hash, hash}` for chain checks |
| `payload` | The source payload after redaction or per-viewer projection. It is not validated against the source type's schema, because redaction removes required fields |
| `redacted` | Optional list of the `payload.` paths removed |

Recipients verify a projection against the host key they pinned, never against the sender's key. The host delivers the *original* envelope only when no field is redacted for that recipient and the event is not viewer-specific; otherwise it delivers a projection. `scope.redact` applies to every recipient except the host and the Steward, so any event with a non-empty `redact` is delivered to everyone else as a projection. A per-member `coalition.propose` (each member sees only its own assignments) is likewise a projection. The projection's own `scope` is the recipient. The delivery form is one function of three facts: a recipient outside the scope gets no delivery (a sender gets only its receipt); inside the scope, a redacted or viewer-specific event is a projection; any other event is the original.

## Message types

Twenty types in v0.1: eleven that members, vaults and edges send and nine that only the host sends. Payload fields listed are the required ones; each type has its own JSON Schema in `schemas/coalition/v0/`.

| Type | From, to | Required payload fields | Notes |
|---|---|---|---|
| `coalition.charter` | Host to members | `goal`, `roles`, `rules`, `deadline`, `deciders`, `revision`, `created_at`; optional `pack`, `budget`, `count_trusted` | `deciders` (non-empty) are the participants who decide plans; an updated charter carries `revision` + 1 and members re-accept it |
| `coalition.join` | Member to host | `card_url`, `owner_key`, `owner_proof`, `roles_requested`, `surfaces`, `vault` (`local` or `hosted`) | `owner_key` is an Ed25519 JWK; `owner_proof` binds it to the participant (see Owner authority). The host replies with granted roles |
| `coalition.leave` | Member to host | none (a reason is optional and never required) | Withdraws the member's open offers |
| `coalition.observe` | Edge to host | `source` (`voice`, `camera`, `chat`, `device`, `document`), `content`, optional `evidence_ref` | Scoped to who may see the source |
| `coalition.need` | Host to members | `need_id`, `description`, `requirements`, `window` | Publishing a need creates a task with the same ID in status `open` |
| `coalition.offer` | Member to host | `offer_id`, `target` (a need or task), `capacity`, `cost`, `valid_until` | `cost` has `minutes`, `money` and `effort`; no free text |
| `coalition.query` | Host to vault | `query_id`, `kind` (`feasible`, `cost`, `availability`), `subject`; optional `deadline_ms`, `task_id` | `deadline_ms` defaults to 10,000. A query asked in planning a task carries its `task_id` |
| `coalition.answer` | Vault to host | `query_id`, `result` (`yes`, `no` or a cost) | The only thing a vault ever returns |
| `coalition.match` | Vault to vault, relayed by the host | `match_id`, `task_id`, `peer`, `round` (`setup`, `request`, `response`), `blob`, `reveal` (`overlap` or `count`) | The host relays opaque blobs and cannot read them (see Private set intersection). `task_id` is the task the exchange concerns |
| `coalition.propose` | Host to members | `proposal_set_id`, `plans` (each with `plan_id`, `revision`, assignments and objective scores), `decision_deadline` | Each member sees only its own assignments (a projection). The tasks it covers are those its assignments name |
| `coalition.tension` | Host to deciders | `tension_id`, `revision`, `task_ids` (non-empty), `options`, `tradeoffs`, `deciders`, `decision_deadline` | `task_ids` are the tasks the tension holds in `proposed` |
| `coalition.decide` | Member to host | `subject`, `choice`, `consent` (true or false), `decided_at`, `consent_sig` | `consent_sig` is by the owner key |
| `coalition.commit` | Member to host | `commitment_id`, `task_id`, `status` (`pending` or `withdrawn`); optional `revision` | `commitment_id` is a ULID the member mints when it creates a commitment. Never `approved`: approval is an owner-signed `coalition.decide` |
| `coalition.ripple` | Any participant | `change`, `invalidates` (task IDs) | Scoped like the change it reports |
| `coalition.say` | Member to host | `to` (`room` or a participant ID), `text` (1 to 280 characters), `intent` (`ask`, `answer`, `trade`, `caveat`, `agree`, `disagree`); optional `re` (the event ID it answers) | One line an agent says to the room or to one seat. Public to the room; `to` names who it is for, not who may see it. It changes no task and binds no one |
| `coalition.done` | Member to host | `task_id`, `evidence` (each with `kind`, `ref`, `verified_by`) |  |
| `coalition.dissolve` | Host to members | `reason` (`completed`, `deadline`, `cancelled`, `budget`), `skills_written` | Final message of a Coalition |
| `coalition.projection` | Host to members | `source`, `payload`; optional `redacted` | Host-signed; see Projections |
| `coalition.receipt` | Host to the sender | `coalition_id`, `seq`, `head_hash` | Host-signed; see Acknowledgements and receipts |
| `coalition.tool` | Host to members | `seat`, `agent`, `tool`, `args`, `result`, `status` (`started`, `done`, `failed`), `ms`, `refs` | What the host saw an agent do: a model call, a private set intersection round, a Steward review, an outside agent's tool call or A2A message. See Tool activity |

Errors travel as `coalition.error` with a `code`, a `detail` and the `ref` of the event they answer (see Errors). `coalition.error` is a payload type the host sends but not one of the twenty.
### Tool activity

`coalition.tool` lets everyone in a Coalition watch the agents work. The host records what it observes and nothing a member claims: a member, vault or edge that sends `coalition.tool` is refused with `not_authorized`.

- `seat` is the participant the activity belongs to, or `host` for the host's own work (the Gardener, the Steward). `agent` is a display label such as `hosted`, `mcp`, `a2a`, `gardener`, `steward`, `vault` or `device`. `tool` names the call as `<family>:<name>`, for example `model:offer`, `psi:compare`, `steward:review`, `mcp:make_offer`, `a2a:offer`.
- A call is recorded as one event with `status: "started"` and one with `done` or `failed`; the second carries the first's `event_id` as its `causation_id`, and `ms` is the measured duration (0 on a start). A host MAY record an instant activity, such as a Steward review, as a single `done` event.
- `args` and `result` are one line each, at most 200 characters. The host builds them from public facts only: never a value from a vault, a contact detail, a key, a bearer token or the text of a prompt. Before recording, the host runs its deterministic outbound policies over both lines and replaces a line that matches any of them with `withheld`.
- `refs` lists the event IDs the activity produced or read; it may be empty.
- The scope is `{"audience": "coalition"}`. Tool events carry no authority: no lifecycle state changes because of one, and a host MAY stop recording them (for example under load) without changing the outcome of the Coalition.

### Subjects and revisions

Everything a consent, a revision check or a decision is about is named with one shape, everywhere (decide, consent requests, stale-subject checks):

```json
{ "kind": "plan" | "tension_option" | "commitment" | "charter" | "task", "id": "<ULID>", "revision": 1 }
```

| `kind` | `id` | `choice` in a decision |
|---|---|---|
| `plan` | `plan_id` | The `plan_id` |
| `tension_option` | `tension_id` | An `option_id` of that tension |
| `commitment` | `commitment_id` | The `commitment_id` |
| `charter` | the `coalition_id` | The `coalition_id` |
| `task` | `task_id` | The `task_id` |

For every kind except `tension_option`, `choice` MUST equal the subject `id`; `consent` carries the yes or no.

The host assigns revisions. An object starts at revision 1 and the revision goes up by 1 on every change to it. The producers expose the current revision: `propose` in each plan's `revision`, `tension` and `charter` in `revision`, and `commit` through the consent request and the projection delivered to its decider (a member omits `revision` when it creates a commitment, which starts at revision 1, and gives the revision it is withdrawing when it withdraws one). Recording a decision compares the decision's revision with the current revision atomically, in the same transaction that records it. Any other revision, older or newer, fails with `stale_subject`. A change to the subject supersedes every pending consent request for an older revision.

### Owner authority

Agent authority and owner authority are separate.

- **At join**, the member sends `owner_key`, an Ed25519 JWK `{kty: "OKP", crv: "Ed25519", x, kid}`, and `owner_proof`: a compact JWS (detached payload) made with the owner key over the JCS form of `{"coalition_id", "participant", "card_url", "owner_key"}`, where `participant` is the envelope's `on_behalf_of`. The host verifies the proof under the key it carries, checks that the key differs from the agent key, and pins it for that participant. Join is refused with `schema_invalid` or `bad_signature` otherwise. The host MUST reject a join whose owner key (compared by RFC 7638 JWK thumbprint) is already pinned to another participant in the same Coalition, with error `not_authorized`.
- **Every `coalition.decide`** carries `decided_at` and `consent_sig`: a compact JWS (detached payload) by the OWNER key over the JCS form of `{"coalition_id", "participant", "subject", "choice", "consent", "decided_at"}`, where `participant` is the envelope's `on_behalf_of`. The host verifies it against the pinned owner key of that participant, and a consent signed for another participant fails; a failure is `bad_signature`. The agent's envelope signature alone never makes a decision count, and a `consent_sig` made with the agent key fails.
- **Through MCP**, the server's hosted owner key signs a decision only after the person answers an MCP elicitation for that exact subject and revision (see The CoalitionKit MCP server).

## Target authorization

A message must pass two independent tests: the scope rules (who may see what) and the authorization matrix below (who may send which type about which objects). Being able to see an object, or being named in a scope, never authorizes an action on it. The host checks the matrix after the stage and task-status check and before it applies the message. A failure answers `not_authorized`, except for `decide`, which answers `not_a_decider`.

| Type | Who may send | About which objects |
|---|---|---|
| `join` | An agent with a valid signed card, named by the invitation it joined by, that has never been a member | Itself; `on_behalf_of` is its owner. A participant that left does not rejoin in v0.1 |
| `leave` | A member | Itself only |
| `observe` | An Edge, or a member | Evidence it holds; its scope may be no wider than who may see the source |
| `offer` | A member | A need or task that is `open` or `negotiating` and visible to the sender. The offer counts only once the sender has accepted the current charter revision |
| `answer` | The vault of the participant the query was addressed to | Exactly one open `query_id`, once. A second answer is `not_authorized`; a late one is `deadline_exceeded` |
| `match` | One of the two parties of the exchange | Its own `match_id`, addressed to the `peer` fixed by `setup`. `setup` names a `task_id` in `negotiating`; the host records `(match_id, task_id, responder, requester)` at `setup`, and every later round must repeat that `task_id` and those parties or it is `not_authorized`. `setup` only from the responder, `request` only from the requester, `response` only from the responder, each round once and in order |
| `commit` (create, `pending`) | The agent of the assignee's owner | A task that the decided plan assigns to its owner and that is `decided`; one active commitment per task; a `commitment_id` not used before in the Coalition |
| `commit` (`withdrawn`) | The agent that created it | Its own commitment, `pending` (task `decided`) or `approved` (task `committed`) |
| `decide` | A decider named for the subject: for `plan`, the charter's `deciders`; for `tension_option`, the tension's `deciders`; for `commitment` and `task`, the owner of the assignee; for `charter`, each member for itself | The named subject at its current revision; one answer per decider and revision. Approval of a commitment exists only as an owner-signed `decide` |
| `done` | The agent of the assignee | A task assigned to its owner whose commitment is approved (task `committed`) |
| `ripple` | A member | Tasks visible to the sender only; every ID in `invalidates` must be one |
| `charter`, `need`, `query`, `propose`, `tension`, `dissolve`, `projection`, `receipt`, `tool` (and `error`) | The host only | Rejected from any member, vault or edge |

### Admission by short code and knock

A host MAY admit a participant by means other than a one-use invitation link, as long as every admission still ends in a one-use invitation redeemed by the `join` above; the matrix does not change.

- **Short code.** A host MAY give a Coalition one many-use short code. Presenting it makes the host issue and redeem a one-use invitation for the presenter, so each joiner is a separate participant. The host MUST refuse the code once the opener stops it, the charter deadline has passed, every seat the charter plans is filled, or the Coalition is dissolved, and MUST rate-limit attempts per code and per caller. A refusal MUST NOT name any member or seat holder.
- **Knock.** A host MAY let a stranger knock on a Coalition the opener has chosen to list. The knock gives the stranger a secret that only they hold; the opener answers yes or no. A yes yields exactly one one-use invitation, handed to the knocker once and only on presenting that secret, compared in constant time. A no admits nothing.
- A host erases every short code, knock and arrival record when the Coalition dissolves.

## Visibility scopes and disclosure

Every envelope says who may see it, and the narrowest reading wins. A host MUST NOT deliver an event, or project it onto a surface, for anyone outside its scope.

```json
{ "audience": "participants", "participants": ["p2", "p5"], "roles": [], "redact": ["payload.window"] }
```

| `audience` | Who sees it |
|---|---|
| `coalition` | Every member |
| `roles` | Members holding one of the listed roles |
| `participants` | Only the listed participants |
| `self` | Only the sender's own owner |
| `host` | The host and the Steward only |

**Disclosure ladder**: what a participant reveals rises one step at a time, and only as far as their own policy allows.

| Level | What others learn | Carried by |
|---|---|---|
| 0 | The signed card: who the agent speaks for and what roles it can play | `coalition.join` |
| 1 | Yes, no or a cost for a specific question | `coalition.answer`, `coalition.offer` |
| 2 | The overlap of two private sets, or only its size | `coalition.match` |
| 3 | The plan they are part of | `coalition.propose`, scoped per member |
| 4 | Details needed to do an assigned task (an address, a time) | `coalition.commit` and `coalition.done`, scoped to the assignees |

**Rules**

- There is no default scope: `scope` is required, and a sender that means only its own owner says `self`.
- Anything the host derives (a plan, a summary, a tension's text, a surface, a lesson written at dissolve) takes the narrowest scope of the events it came from, and the host refuses to widen it.
- **Redaction does not survive derivation.** A redaction path names a field of its own event, and a derived output renames and rewrites fields. So an output derived from a source that has a non-empty `redact` list is scoped `host` and carries no `redact`, unless the host built it from that source's redacted projection only (the payload with the paths already removed). Such a source counts as *projected*: it keeps its audience and contributes no redaction paths. A derived scope never carries `redact`.
- Scopes apply on every path out of the host: deliveries, AG-UI snapshots and deltas, MCP reads, log replays, exports and traces.
- Business and machine participants receive only events scoped to them and the tasks assigned to them.
- The Steward sees every event but emits only verdicts; it never forwards content.
- Redaction removes the listed fields before delivery to anyone except the host and the Steward, and the delivery is then a projection signed by the host.

### The narrowest scope of several sources

The *narrowest scope of its sources* is the intersection of the resolved principal sets of the sources, resolved at derivation time, not when a source was written:

| Source `audience` | Resolved principal set |
|---|---|
| `coalition` | Every member now |
| `roles` | Members who hold any listed role now |
| `participants` | The listed participants who are members now |
| `self` | The source sender's owner (the source's `on_behalf_of`) |
| `host` | Nobody |

An empty intersection becomes `host`. A source with a non-empty `redact` list that is not projected makes the result `host` (see Redaction does not survive derivation). The derived scope is written as `coalition` when every source is `coalition`, as `roles` when every source lists the same roles, and otherwise as `participants` with the sorted intersection (or `host` when it is empty). The reference function is `resolve_narrowest` in `coalitionkit_contracts`; the cases are in `spec/vectors/scope.json`.

## Lifecycle rules and ordering

The host is the single writer of a Coalition's log, so its `seq` is the order. The Coalition has one stage; every task has its own status, so a ripple re-opens only the tasks it touches.

**Two levels.** The *stage* governs Coalition-level messages only: `join`, `leave`, `observe`, `decide` about the charter and `dissolve`. The *task status* governs every message about a task (`answer`, `match`, `offer`, `propose`, `tension`, `decide`, `commit`, `done`, `ripple`) in any stage from Gather to Live, whatever the stage says. A message rejected by either level gets `stage_mismatch`.

**Stages**

| Stage | Coalition-level messages accepted from members and edges | Messages about tasks | Moves on when |
|---|---|---|---|
| Germinate | `join`, `leave`, `decide` (charter) | None | The charter's required roles are filled, or the organizer starts it |
| Gather | `join`, `leave`, `observe`, `decide` (charter) | By task status | The Gardener has enough needs and offers to plan |
| Negotiate | `leave`, `observe`, `decide` (charter) | By task status | A proposal set passes the Steward |
| Decide | `leave`, `observe`, `decide` (charter) | By task status | Every named decider has answered, or the decision deadline passes |
| Act | `leave`, `observe`, `decide` (charter) | By task status | Every commitment is approved or withdrawn |
| Live | `leave`, `observe`, `decide` (charter) | By task status | All tasks are done, or the deadline passes |
| Dissolve | `leave` | None | Terminal |

**Task status** moves `open` → `negotiating` → `proposed` → `decided` → `committed` → `done`, or to `withdrawn` from any status before `done`. A task starts `open` when its need is published.

| Task status | Accepted about the task | Moves to |
|---|---|---|
| `open` | `offer`, `ripple` | `negotiating` when the host starts planning it (see below) |
| `negotiating` | `answer`, `match`, `offer`, `ripple` | `proposed` when a plan or tension covering it passes the Steward |
| `proposed` | `decide` (plan, tension option or task), ripple | `decided` when every named decider has consented |
| `decided` | `commit` (`pending`, or `withdrawn` for a pending commitment), `decide` (commitment or task), `ripple` | `committed` when the assignee's owner approves the commitment; `negotiating` when the pending commitment is withdrawn |
| `committed` | `done`, `commit` (`withdrawn`), `ripple` | `done` |
| `done`, `withdrawn` | Nothing | Terminal |

**Planning starts without a message of its own.** A task moves from `open` to `negotiating` at the first host-originated `query` carrying its `task_id`, or `propose` or `tension` naming it, whichever the log holds first; replaying the log gives the same status. A `propose` or `tension` in `open` passes through `negotiating` in the same transaction.

The host also sends `query`, `propose` and `tension` about a task in the statuses where they apply (`negotiating` for queries and proposals; `negotiating` or `proposed` for tensions). Any refusal in `proposed` or `decided`, a withdrawn commitment, a ripple that invalidates the task, or an expired decision sends it back to `negotiating`. In that same transaction the host marks the task's active commitment (`pending` or `approved`) `superseded` and closes every consent request about the task, its plans and its commitments. A superseded commitment is not active, so the replan can create a new commitment (a new `commitment_id`, revision 1) that needs a fresh owner-signed approval; a decision on a superseded commitment is `stale_subject`. A task not `done` when the Coalition dissolves is closed as `withdrawn`; a `done` sent in Dissolve is `stage_mismatch`.

**Rules**

1. Members MUST treat `seq` as the total order and MAY reorder their local view by it.
2. A refused consent, a withdrawn commitment or a ripple sets the affected tasks back to `negotiating`; the Coalition keeps its stage. Only when every open task is back to `negotiating` does the Coalition itself return to Negotiate.
3. The host MAY send `coalition.dissolve` from any stage on cancellation, deadline or budget exhaustion.
4. Only a decider named for the subject may send `coalition.decide` for it (see Target authorization).
5. **Decisions are per decider.** The first answer wins per (Coalition, `subject.kind`, `subject.id`, `subject.revision`, decider). A later answer from the same decider for the same key is not recorded and gets `not_authorized`. A subject is *decided* when every named decider has consented. For a `tension_option` every decider must consent to the same `choice`: consents naming different options leave no option decided (the tension is *split*) and count as a refusal. Any refusal sends the subject's tasks back to `negotiating`. Answers from different deciders arrive in `seq` order, are all recorded, and the last consent decides the subject. When one plan of a proposal set is decided, the other plans of that set are superseded. A tension whose options name plans (an `option_id` equal to a `plan_id`) decides the chosen plan when the option is decided: that plan is decided with its assignments, for all of its tasks (including those the plans agreed on and the tension therefore did not hold), and the other plans of its set are superseded, so no separate decision on the plan is needed.
6. A decision names the revision of the subject it answers and the host compares it atomically as described under Subjects and revisions; a decision on any other revision is refused with `stale_subject`.
7. A commitment made by an agent for an absent owner stays `pending` until that owner's own `coalition.decide`, with the owner's `consent_sig`, approves it. The member's `commit` carries `pending` or `withdrawn`; `approved` is a host-side state reached only through that decision.
8. Delivery is at least once; receivers deduplicate by `event_id`.
9. **Decisions expire.** `propose` and `tension` carry `decision_deadline`, an absolute RFC 3339 time that applies to every plan or option in them. A `commitment`, `task` or `charter` subject has no deadline of its own; it ends with the Coalition's `deadline`. A decision the host accepts after the deadline (its `ts` is later than `decision_deadline`) is not recorded and gets `deadline_exceeded`. A subject that is undecided when its deadline passes is *expired*: its consent requests close, its tasks go back to `negotiating` and no commitment is created. Expiry is a pure function of the log and the clock: before applying any event, and before answering any read, the host applies the expiry of every subject whose deadline is earlier than that event's `ts` (or the read's time), in the same transaction. A new revision of a subject carries its own `decision_deadline`.

### Charter acceptance

A member accepts a charter with `coalition.decide` on a subject of kind `charter` at the charter's current `revision`, owner-signed like any decision. It is allowed in every stage before Dissolve. A member's offers and commitments count only after it has accepted the current charter revision. A new charter revision suspends the member's open commitments (a host-side flag) until the member accepts the new revision; a suspended commitment cannot be reported `done`. An answer that refuses the charter leaves the member without counting offers or commitments.

## Errors, timeouts and retries

Errors are messages, never silence. Every rejected envelope gets a `coalition.error` scoped to its sender, and a true duplicate gets its original acknowledgement back. When a rejected envelope has no valid `event_id`, `ref` is a ULID the host mints for the purpose.

| Code | Meaning | Sender should |
|---|---|---|
| `schema_invalid` | The envelope or payload fails its JSON Schema | Fix and resend with a new `event_id` |
| `bad_signature` | The envelope signature does not verify against the sender's pinned card key, or a `consent_sig` or `owner_proof` does not verify against the owner key | Re-sign; check key rotation |
| `sender_mismatch` | `sender` or `on_behalf_of` differs from the authenticated connection | Drop the message |
| `unknown_participant` | The sender has not joined, or has left (any type but `join`) | Join first |
| `extension_not_activated` | Coalition data arrived on a call without the `A2A-Extensions` header | Resend with the header |
| `stage_mismatch` | The type is not accepted in the current stage, or the task is not in the right status | Wait for the stage, or drop the message |
| `scope_violation` | The scope names someone the sender may not address, or is wider than its sources | Narrow the scope |
| `not_authorized` | The sender may not send this type about this object (see Target authorization) | Drop the message |
| `not_a_decider` | A decision from someone not named for the subject | Drop the message |
| `stale_subject` | The decision answers a revision other than the subject's current one | Read the current revision and decide again |
| `duplicate_mismatch` | The `event_id` is already taken in this Coalition by another sender or by different bytes; `detail` is empty | Send under a new `event_id` |
| `steward_blocked` | The Steward refused it; `detail` gives the policy ID | Revise, or ask a human |
| `deadline_exceeded` | The answer arrived after its query's deadline, or a decision after its `decision_deadline` | Nothing; the sender was counted as abstaining, or the subject expired |
| `rate_limited` | The sender exceeded its rate | Back off as told in `detail.retry_after_ms` |
| `budget_exhausted` | The Coalition's model budget is spent | Nothing; the Coalition continues without model calls |
| `pack_violation` | A pack policy forbids the action | Revise |

**Check order.** The host checks in this order and stops at the first failure: (1) `extension_not_activated`; (2) `sender_mismatch`, from `sender`, `on_behalf_of` and `event_id`, which it reads before schema validation; (3) the idempotency lookup, answering a replay or `duplicate_mismatch`; (4) `rate_limited`; (5) `schema_invalid`; (6) `unknown_participant`, except for `join`, which is checked instead against the invitation and the authenticated connection (`not_authorized` if either fails, or if the sender is or was a member) and registers the participant atomically with its acceptance; (7) `bad_signature`, including `consent_sig`, and for `join` the card signature and `owner_proof`; (8) `stage_mismatch`, stage then task status; (9) `not_authorized` or `not_a_decider`; (10) `scope_violation`; (11) `deadline_exceeded` for a decision past its `decision_deadline`, then `stale_subject`, both at recording time inside the transaction; (12) `pack_violation`, then `steward_blocked`. `deadline_exceeded` and `budget_exhausted` apply where their conditions arise.

**Timeouts**: each `coalition.query` MAY carry `deadline_ms`; when it is missing the deadline is 10,000 ms (a pack may change the default), and silence counts as abstaining. Decisions carry `decision_deadline` in their tension or proposal (see Lifecycle rules, rule 9).

**Retries**: senders retry transport failures with exponential backoff and jitter, reusing the same `event_id` and the same bytes. The host retries delivery to a member up to a configured limit, then marks it unreachable and notifies its owner through another surface.

## Private set intersection (PSI)

`coalition.match` carries a two-party PSI between two vaults. The host relays; it cannot read a blob. This section describes the reference implementation (`packages/vault`, `psi.py`) byte for byte.

**Scheme.** ECDH-PSI over the ristretto255 group (RFC 9496), with a fresh secret scalar per party and exchange. Group operations are libsodium's. The two parties are the *requester*, who learns the result, and the *responder*. Both pin the other's Ed25519 signing key through the authenticated identity layer before the exchange; a key taken from the relay is never trusted. Every `coalition.match` message carries `peer`, the participant ID of the party the message is addressed to, and `task_id`, the task the exchange concerns; a receiver refuses a message whose `peer` is not its own participant ID or whose `task_id` differs from the one in `setup`. `task_id` is bound by the sender's envelope signature and by the host's exchange record (see Target authorization), not by the context digest, so the digest and the vectors' blobs are unchanged.

**Context digest.** *C* = SHA-256 of the JCS form of the JSON array `["coalition-psi-v1", coalition_id, match_id, requester, responder, reveal]`, where `requester` and `responder` are participant IDs. The order of the pair is part of the binding; swapping the roles, or changing `reveal`, gives a different *C*.

**Element mapping.** An element is an exact Unicode string, not normalized, of at most 4,096 UTF-8 bytes. `H(x)` is `hash_to_group` of the RFC 9380 suite `ristretto255_XMD:SHA-512_R255MAP_RO_` with the domain separation tag `DST = "CoalitionKit-v0.1-PSI-ristretto255_XMD:SHA-512_R255MAP_RO_"` (ASCII), applied to the message `C || JCS(x)` (JCS of a JSON string). Concretely, `expand_message_xmd` with SHA-512 and 64 output bytes (`b0 = SHA-512(0x00 x 128 || msg || 0x00 0x40 0x00 || DST || len(DST))`, `b1 = SHA-512(b0 || 0x01 || DST || len(DST))`, `len(DST)` as one byte), then libsodium's `crypto_core_ristretto255_from_hash` on `b1`. Because *C* is part of the message, points from different exchanges never coincide.

**Rounds.** The responder sends `setup`, the requester sends `request`, the responder sends `response`; each once and in this order. A party that receives a message in any other state refuses it.

| Round | Sent by | Body (before framing) |
|---|---|---|
| `setup` | Responder | `Pr`, the responder's 32-byte channel public point (a fresh random channel scalar times the base point) |
| `request` | Requester | `Pq` (32 bytes, the requester's channel public point), then `AEAD(list of H(x_i)^a)` |
| `response` | Responder | `AEAD(list of request points ^b, then list of H(y_j)^b)` |

*a* and *b* are fresh random scalars. Each party shuffles its own input uniformly before use.

**Blob.** The `blob` of every message is the unpadded base64url (RFC 4648 section 5) encoding of:

| Field | Bytes |
|---|---:|
| ASCII `CKP1` | 4 |
| Round: `setup` = 0, `request` = 1, `response` = 2 | 1 |
| *C* | 32 |
| Round body | variable |
| Ed25519 signature by the sender's signing key over all preceding bytes | 64 |

A receiver rejects a `blob` longer than 94,000 characters; a `match_id`, `peer`, `reveal` or `round` that differs from the exchange it holds; base64url that is not canonical (re-encoding must give the same `blob`); a signature that does not verify under the pinned key; and a magic, round or *C* that differs from the expected one.

**List.** A list is an unsigned 16-bit big-endian count *n*, then *n* entries, each an unsigned 16-bit big-endian length (always 32) followed by a 32-byte canonical ristretto255 encoding. A receiver rejects a count above 1,024, a length other than 32, a truncated list, a non-canonical or invalid encoding, the identity element, a duplicate point and trailing bytes after the last list. The decrypted request body is one list; the decrypted response body is two lists, the first with as many points as the requester sent.

**Channel.** The relaying host sees every blob, so the request and response lists are encrypted and the host cannot compare matching tokens. Let *S* be the ristretto255 scalar multiplication of one party's channel scalar by the other's channel public point (both sides compute the same *S*; a public point that is invalid or the identity is refused).

- Request key `K1` = SHA-256(ASCII `coalition-psi-channel-v1` || *C* || *S*).
- Response key `K2` = SHA-256(ASCII `response` || `K1`).
- Encryption is ChaCha20-Poly1305 (RFC 8439) with a 12-byte all-zero nonce and the 16-byte tag appended to the ciphertext. Each key encrypts exactly one message, so the fixed nonce is never reused.
- The associated data is *C* || ASCII(round) || SHA-256(transcript). For `request` the transcript is the ASCII `blob` of the `setup` message; for `response` it is the ASCII `blob` of `setup` followed by the ASCII `blob` of `request`. The signature binds each body to its context and round; the associated data binds the encrypted lists to the whole earlier exchange.
- The requester derives `K1` from the `setup` body; the responder derives it from the first 32 bytes of the `request` body, and the rest of that body is the ciphertext.

**Limits and reveal.** Each side contributes at most 1,024 elements, and a party refuses duplicate elements in its own input. The longest blob is a `response` with 1,024 elements on each side: 93,068 characters. For `reveal: overlap` the responder returns the request points raised to *b* in the order it received them; the requester raises the responder's points to *a*, finds which of its own points match, and learns exactly those elements of its own set. For `reveal: count` the responder shuffles that first list independently before returning it, so the requester learns only the size of the intersection. In both cases the requester also learns the responder's set size, the responder learns the requester's set size, and the host learns both sizes from the blob lengths. The result reaches the requester only; a responder that wants the overlap runs a second exchange with the roles swapped. A responder that declines sends nothing and the requester treats silence as abstaining after the deadline.

**Threat model.** v0.1 PSI is secure against semi-honest (honest-but-curious) participants only. If both vaults follow the protocol, neither vault nor the relaying host learns any element outside the intersection; the host learns the set sizes. A malicious requester in `count` mode could blind each element with a different scalar and so learn which elements matched, not only how many. Therefore a vault MUST accept `reveal: count` only from a requester that the charter names in `count_trusted`, and otherwise refuse with `not_authorized`; `overlap` is the default and is always available to a requester the vault's own policy accepts. A zero-knowledge proof that one blinding scalar was used for all request points is deferred to v0.2. Low-entropy elements can be guessed by the peer by hashing candidates, so a vault decides which of its sets it will put into an exchange at all. The encrypted channel keeps the relaying host from comparing tokens or testing guesses against them, and the signatures keep it from altering a message undetected.

**Known-answer vectors** are in `spec/vectors/psi.json`. An implementation MUST reproduce them.

## The CoalitionKit MCP server

Any MCP host (Claude, ChatGPT, Cursor, Muse Code) joins a Coalition through this server with the same rights and limits as an A2A member. It targets MCP spec 2026-07-28 and turns each tool call into a signed Coalition envelope on the participant's behalf.

| Tool | Input | Result | Becomes |
|---|---|---|---|
| `list_coalitions` | none | Coalitions this participant belongs to | none (a read) |
| `join_coalition` | `invite` (link or Coalition ID), `roles` | Granted roles and the charter | `coalition.join` |
| `my_view` | `coalition_id`, `device` | A plain-text summary, with the surface's data as structured content | none (a read) |
| `pending_questions` | `coalition_id` | Open queries addressed to this participant | none (a read) |
| `answer_question` | `coalition_id`, `query_id`, `result` | Accepted or an error | `coalition.answer` |
| `make_offer` | `coalition_id`, `target`, `capacity`, `cost` | The offer ID | `coalition.offer` |
| `commit` | `coalition_id`, `task_id`, and either `status: pending` (create) or `status: withdrawn` with `commitment_id` | The commitment ID and its status | `coalition.commit`, with the same rules as A2A |
| `report_ripple` | `coalition_id`, `change`, `invalidates` | Accepted or an error | `coalition.ripple` |
| `accept_charter` | `coalition_id` | The recorded acceptance | `coalition.decide` on the charter at its current revision |
| `decide` | `coalition_id`, `subject`, `choice`, `consent` | The recorded decision | `coalition.decide` |
| `approve_commitment` | `coalition_id`, `commitment_id` | The approved commitment | `coalition.decide` on the commitment |
| `report_done` | `coalition_id`, `task_id`, `evidence` | Accepted or an error | `coalition.done` |
| `leave_coalition` | `coalition_id` | Confirmation | `coalition.leave` |
| `web_search` | `coalition_id`, `query` | Web results (`title`, `url`, `snippet`), or `steward_blocked` when the host refuses the query | none (a read of the open web through the host) |

**Resources**: `coalition://{id}/charter`, `coalition://{id}/my-tasks` and `coalition://{id}/log?since={seq}`, each filtered to the caller's scopes. The 2026-07-28 spec is stateless, so every read is authorized on its own; nothing carries over from an earlier call. Tool results are rebuilt from an allowlist of fields, because hosts copy structured content into the text the model reads. A log read returns originals only where nothing is redacted for the caller, projections elsewhere (each carrying its source's `prev_hash` and `hash`), and stubs for events outside the caller's scope.

**MCP Apps**: one versioned view, `ui://coalitionkit/surface-v1.html`, renders the participant's live surface inside the host, so a Claude or ChatGPT user sees the same screen as a web user. The Coalition ID travels as tool data, never in the URI, because hosts cache views by URI; a breaking change to the view ships under a new URI. The view is one bundled HTML file under the default closed CSP, every tool it calls is authorized again on the server, and every tool also returns readable text for hosts that render no views.

**Auth**: MCP's OAuth-based authorization; each access token maps to exactly one participant. The server holds two hosted keys for that participant and never a shared key: the agent key signs envelopes, and the hosted owner key signs consent.

**Writes need a person**: `decide`, `approve_commitment` and `accept_charter` ask the person through MCP elicitation inside the tool call (multi-round tool results in the 2026-07-28 spec). The server's hosted owner key signs the `consent_sig` only after the person has answered an elicitation for that exact subject and revision, and records only the answer given there. For `approve_commitment` and `accept_charter`, whose input carries no revision, the server reads the subject's current revision when it builds the elicitation, shows it to the person, and signs for exactly that revision; if the revision changes before the answer, the elicitation is void and the host's `stale_subject` check stands. A confirmation flag in the tool's arguments is never trusted, because a model or an MCP App view can set it. `commit` and `report_ripple` need no elicitation: neither carries owner authority.

## Surfaces: AG-UI and A2UI

Surfaces use AG-UI 1.0 for the live stream and A2UI v0.9.1 (the current stable release; messages carry `"version": "v0.9"`) for the components. A2UI v1.0 is a release candidate, and moving to it changes behaviour as well as names (deletion, themes, duplicate surfaces), so v0.1 stays on v0.9 and the move needs a separate protocol revision.

**Hosted member conveniences.** With the same viewer bearer token and origin rules as `/v1/agent/answers`, `POST /v1/agent/offer` accepts `{need_id, cost?, window?, ext?}`. It signs and submits `coalition.offer` as that viewer’s hosted member and returns `{seq, offer_id}` or the host refusal code. Capacity is one; cost defaults to zero minutes and money with low effort; the offer expires at the need window’s end, or the supplied window’s end. Core validation precedes pack extension validation (`schema_invalid`). Private extension properties are refused with HTTP 422 before submission. A member with their own agent receives HTTP 409, “your agent sends offers”. These conveniences create only member messages that the member could send itself.

`POST /v1/agent/vault` accepts `{values: {key: value}}`, merging values into only the authenticated member’s encrypted hosted vault state. `GET /v1/agent/vault` returns `{keys: [...]}` only, never values. Non-hosted members receive 409. No participant selector is accepted. Values stay in the vault: they never enter the log, projections, or Steward input, and are erased with hosted state at dissolution.

**Hosted rooms.** A server MAY run hosted seats itself. It uses only what a member or the host could send. A helper is a hosted member whose card and labels say it is an agent; it holds its own keys, is never named in `deciders`, and its owner key signs only its own charter acceptance and its own commitments. When seats remain open, the owner MAY begin: the host issues a charter revision whose `deciders` are the seated people, and each of them accepts it as usual. A result is a `coalition.observe` with `source: "document"` whose `content` is a JSON document holding `result`, `need_id`, `kind`, `title`, `source`, `sources`, `components` and `data`; the components pass the same host validation as any tree. `kind` is `place`, `schedule`, `budget`, `list`, `draft` or `image`. The viewer's result surface carries `data` as its data model, every number written as a string, so a tree may bind to it. An `image` result's `data` is `{hash, alt, prompt, width, height}`: `hash` is the SHA-256 of a picture the host keeps, and `GET /v1/room/media/{hash}` serves it, with the viewer bearer token, only to viewers of that Coalition; its data model adds `image.src`, that path. The host builds the prompt from public facts only (the goal and the need) and runs the deterministic outbound policies on it before it leaves the host; a match holds the call and is written down as a stop. `coalition.done` cites it with evidence of kind `result` whose `ref` is that event's ID. An offer made by a hosted seat means "I could do this need, and it would take me about this long": `cost.minutes` is that person's own estimate for that one need, capped per offer by the most time they said they would give to any one job, never summed over offers; `cost.effort` says how well the job fits (`low` for what they prefer, `high` for what they would rather not do). Offers are alternatives; the plans choose among them. A host MAY pass the planner a third objective, the total `effort` of the chosen offers, so plans can differ on time, evenness and preference. The times everyone can do are compared with the PSI messages (`query`/`answer`, then `match` setup, request and response, run as a chain by the first person) and only the shared times are published, in a `coalition.observe` whose `content` is `{"common": 1, "task_id", "slots", "compared"}`; how many of a person's own times stayed private is shown to that person only. A set a bound pack declares under `compare` is compared the same way and published as `{"common": 1, "set", "values" or "count", "compared"}`; how many of a person's own values stayed private is shown to that person only. A change a person says is a `coalition.ripple` on only the needs it touches; a need that is already `done` cannot ripple, so the host publishes a successor `coalition.need` and the older result is marked replaced. A minted device MAY take a hosted seat the same way as a helper, only after its Mint attack suite passed and its owner signed `consent_payload(manifest_hash, "approve", {})` with their own owner key; its card and labels say it is a device, it is never named in `deciders`, and the minted MCP server it fronts receives no keys, tokens or store access. A device seat offers only on the needs that require it, and only on a hold it has already taken through the minted `hold_slot` tool; the hold is confirmed or released with the owner's signature over that one operation once the plan is decided. Its readings are `coalition.observe` with `source: "device"` whose `content` is `{"device", "readings": [{"field", "value", "unit", "threshold", "over"}]}`, and a reading that crosses its template threshold is a `coalition.ripple` from that seat on the needs that name the device. Before plans, and again after a change, the agents talk in a Talk stage of at most two rounds: in each round every seat's agent reads the thread and the offers and either sends one `coalition.say` or passes, and may then revise its own offers. A hosted seat's agent sees only public events and its own vault, and the host refuses to send a line that holds one of that seat's own private values unless the person asked it to say those words; the refusal is written down as a stop. The stage waits a bounded time for agents a person brought, then the plans follow. A message the Steward holds on a hosted seat's behalf is written down as a stop (seat, recipient, policy, explanation) and is not sent again with the same words. `POST /v1/room/begin`, `/v1/room/brief`, `/v1/room/say`, `/v1/room/done`, `/v1/room/mint`, `/v1/room/mint/approve` and `/v1/room/mint/frame` take the viewer bearer token and act only as that viewer's hosted member. `POST /v1/room/voice` (a mono 16-bit PCM WAV of at most 20 seconds) and `POST /v1/room/photo` (a PNG, JPEG or WebP image with `question_id` or `purpose: "say"`) take the same token and only read: they return words, and for a question an answer in that question's closed kind, that the person may change and MUST confirm through `/v1/room/brief` or `/v1/room/say` before anything is saved or sent. The audio and image bytes are held only for the call and never enter the log or the store. A sentence the person said aloud and confirmed is sent with `via: "voice"` and its `coalition.observe` carries `source: "voice"` (`source: "camera"` for one read from a photo); a change said aloud is an ordinary `coalition.ripple`. The feed snapshot MAY carry `stage`, `cost_meter` and a per-viewer `room` key; these carry no authority, and values from a viewer's vault appear only in that viewer's own `room.mine`, including `room.mine.inputs`, the viewer's own recent voice and photo readings. A hosted room records its agents' model calls, comparison rounds, Steward reviews and outside agents' MCP and A2A calls as `coalition.tool` events (see Tool activity).

**Standing room.** A public host MAY keep one standing room: when none is open it creates a Coalition from a fixed goal on its own clock, optionally bound to a pack, owned by the host's own hosted seat, with its short code listed publicly. Visitors join it by that code; on such a host `POST /v1/genesis/start` requires a start code and `POST /v1/genesis/draft` the admin token, so a visitor cannot start a room. The host begins the room once people have had time to arrive, dissolves it with reason `completed` when its time is up (vaults erased, lessons written as for any dissolve), and then forms a new one. `GET /v1/standing` returns the open standing room's goal, code, seats, the time left and its model spend, and never a token. A host MAY cap the model spend of each room: past the cap the room's model calls are not sent, the rules answer in their place, and the room says so once in its activity.

**Web search.** A host MAY let agents search the web. Search is off unless the host names a provider. A query MUST be screened on the host before it leaves: the deterministic core policies run on it as they would on a message to the whole Coalition, and a query holding a street address or any private value a member's vault holds is refused and sends nothing. A hosted seat's query is built from public facts only (the goal and the need). An outside agent searches through the MCP tool `web_search` under the same screen. A result built from a search keeps the pages in `data.web` as `{title, url, snippet}`, each an http(s) URL the search itself returned, and a named place carries its `url` and `provenance: "search"`; a screen shows only http(s) links from it. The feed MAY list the searches in `room.search`; they hold only the screened queries.

**Two sessions per viewer.** A feed session carries state and surfaces and never interrupts. An agent session carries messages to that person and their consent requests. A consent request outlives any connection: it is stored on the host, the first answer recorded per decider wins, and the interrupt is only how it is shown. The person's answer is turned into an owner-signed `coalition.decide`; a surface never sends a decision the owner key did not sign. The feed sends a keep-alive comment every 15 seconds and rotates every 10 minutes; reconnecting starts a new run with a fresh snapshot, since AG-UI has no resume by event ID.

| Coalition event | AG-UI event | What the renderer does |
|---|---|---|
| A viewer connects | `RUN_STARTED`, then `STATE_SNAPSHOT` of this viewer's own projection, on the feed session | Draws the fallback layout at once |
| An accepted event that changes this viewer's projection | `STATE_DELTA` (RFC 6902 JSON Patch) computed on the viewer's projection, never on the shared state | Updates only the changed fields; flashes them as a ripple |
| A new or changed composition | A2UI `createSurface` once per surface, then `updateComponents` and `updateDataModel`, carried as `ACTIVITY_SNAPSHOT` on the feed session | Replaces the fallback with the composed tree |
| A consent request (`coalition.tension`, a plan to accept, a commitment to approve, a new charter revision) | A consent record on the host, shown as an interrupt on the deciding person's agent session only | Shows the decision card; the answer resumes with a new run that covers every open interrupt |
| A Gardener planning step | `STEP_STARTED`, `STEP_FINISHED` on the feed session | Shows that agents are working, and on what |
| A message from an agent to a person | `TEXT_MESSAGE_START`, `TEXT_MESSAGE_CONTENT`, `TEXT_MESSAGE_END` on the agent session | Streams the text into the surface's message area |
| A tool call visible to this viewer | `TOOL_CALL_START`, `TOOL_CALL_END` | Feeds the wiring overlay |
| A failure | `RUN_ERROR` | Keeps the last good surface, shows the error quietly and reconnects with a new run |

**The v0.1 catalog** is a closed custom catalog, `coalitionkit/v0_9`; renderers refuse any other catalog ID. Its normative definition is `spec/catalog/coalitionkit-v0_9.json`: 201 components in 11 families (foundations; shell, doors and templates; conversation and calls; forms and flows; coalition and people; needs, offers, tasks and plans; places and time; privacy and consent; live and proof; mint and machines; channels, ending and memory), each with its typed props, events, states and the doors it renders on. Every prop declares a type (string, number, integer, boolean, datetime, id, enum with its values, binding, subject, scope, child, children, array, object or any), whether it is required, and may instead be a data binding `{"path": ...}`; numbers are bound `{value, event_ref}`; consent components carry a required `subject` `{kind, id, revision}` and a `decision_deadline`. The host validator loads this file and enforces the types; values held in a member's vault never appear in a tree. The core catalog is domain-agnostic. A Discipline Pack may add components for its own discipline as a pack catalog extension, accepted only while that pack is active; a pack component never replaces or renames a core component.

Components the protocol itself depends on, and their key props:

| Component | Shows | Key props |
|---|---|---|
| Card, Panel, Grid | One object, a group, a layout | `title`, `fields`, `status`, `provenance`, `children` |
| List, Table | Several objects | `items` or `rows`, `columns`, `sort` |
| Timeline, Gantt | Tasks and commitments over time | `items` with `start`, `end`, `assignee` |
| Form, ChoicePicker | Input from a person | `fields` or `options`, `submit_event` |
| ConsentCard, ApprovalButton | A consent request | `subject` (kind, id, revision), `consequence`, `decision_deadline` |
| PlanCompare | Plan universes side by side | `plans`, `objectives`, `rejected` |
| TensionCard | A conflict and its trade-offs | `options`, `tradeoffs`, `deciders` |
| Progress, Meter | A value against a goal or range | `value`, `min`, `max`, `unit` |
| MapView | Places | `points`, `routes`, `areas` |
| MediaWithMasks | An image or video frame with segmentation masks | `media_ref`, `masks`, `labels` |
| EvidenceCard | Proof that a task was done | `kind`, `ref`, `verified_by` |
| DecisionLog | Who decided what, and why | `entries` |
| WiringDrawer | The protocol message behind any element | `event_ref` |

Every component has an accessible label and a right-to-left layout, and declares the doors it renders on: wide, compact, message, voice, lens (glasses) and mcp-app. The host validates every tree before sending it: known components only, one root, no orphans or cycles, at most 500 components and a depth of 24, no HTML in props, and every number bound to the event it came from. Renderers show values as text only. A tree that fails validation is replaced by the fixed layout.

## Discipline Pack format

A pack is a folder of data the loader validates before a Coalition can use it. A pack that fails validation never loads, and the loader's report says which rule it broke.

| Key in `pack.yaml` | Required | Meaning |
|---|---|---|
| `name`, `version` | yes | Unique name and semantic version |
| `core` | yes | The range of core versions it works with, such as `>=0.1,<0.2` |
| `roles` | yes | Role IDs and what each may do: `charter`, `offer`, `decide`, `decide_own`, `commit` |
| `vocabulary` | no | Words shown on screens for core objects (task, resource, need) |
| `schemas` | no | JSON Schemas for the `ext` object of needs and offers (keys `need`, `offer`); the keys `task` and `resource` are accepted for later versions and not applied in v0.1 |
| `policies` | no | Steward policy files |
| `skills` | no | SKILL.md files loaded by agents that join |
| `views` | no | Component order per role and device |
| `mint` | no | Extra Mint templates, each with its own tests |
| `connectors` | no | MCP servers the pack needs, run out of process |
| `strategy` | no | Allocation strategy and fairness settings (see Strategy names below) |
| `suggest` | no | How a host may offer this pack for a goal typed in plain language: `keywords` (lowercase words or short phrases) and `examples` (whole example goals), at most 50 of each. A host that suggests packs MUST also offer "no pack", and a suggestion never binds a pack by itself |
| `lessons` | no | Lesson templates (Markdown with `{{placeholders}}` from a fixed set) the host fills from the log at Dissolve and writes as skills |
| `compare` | no | Named private sets every seat is asked for and the room compares by PSI (see Compared sets below) |
| `public` | no | Questions every seat is asked whose answers are published to the room, such as the city a person is in (see Public questions below) |
| `evals` | yes | At least one scripted scenario |
| `acceptance` | no | Relative path to the whole-journey acceptance YAML described below |

**Compared sets.** `compare` lists at most four named private sets. The room asks every seated person for each one, keeps the answers in each seat's vault and compares them by PSI, so the room learns only what the set's `mode` allows:

```yaml
compare:
  - id: colours                # lowercase letters, digits and hyphens, starting with a letter; at most 32
    label: Colours we all like
    question:
      text: "Which of these colours would you be happy with?"
      kind: choice             # choice, slots or text
      options: [red, blue, green, yellow, white]
      why: "Only the colours everyone picked are shown."   # optional
    mode: overlap              # overlap (default): the shared values; count: only how many
    min_seats: 3               # optional; default every seated person
```

`question.kind` is one of the closed brief kinds. `choice` needs two to twelve distinct options and lets a person pick any number of them; `slots` offers the room's time slots; `text` takes a short list separated by commas or new lines, and each value is trimmed, its spaces collapsed and lowercased before it is compared. `slots` and `text` take no options. `amount` is refused, because a set is matched value by value. Ids are distinct. The loader refuses any other shape and says which rule it broke.

**Public questions.** `public` lists at most two questions whose answers are not private. The room asks every seated person each one beside the agent's own questions; when a person answers, the host publishes the answer to the whole room as a `coalition.observe` from that person's seat with `source: "chat"` and the content `"<label>: <answer>"`. A question marked `search: true` adds the person's answer to the words of that seat's web searches on `place` needs: each seat whose answer differs searches once with the need's title and its own answer only, and the hits of every seat are kept together for the need's result.

```yaml
public:
  - id: city                   # same rule as a compared set id
    label: City
    question: { text: "Which city are you in?", kind: text }   # text, or choice with options
    search: true               # optional; default false
```

Tell people the answer is public: the brief shows the question's `why` line, which by default says the whole room sees the answer. A seat whose own agent acts over MCP gives its answer by writing the vault key `public:<id>` (a string) through `POST /v1/agent/vault`. A published answer is no longer private, so web search does not refuse a query for holding it.

**Core policies.** The Steward ships `no-regulated-advice`, `no-contact-before-consent`, `no-private-field-in-outbound`, `fairness-cap-exceeded` and `no-contact-details-in-room` (blocks a phone number or email address written into a message to the whole Coalition). Each has a known-answer example the Steward must pass before it starts.

**A policy** is checked deterministically before the Steward's model audit:

```yaml
id: no-regulated-advice
applies_to: [coalition.observe, coalition.offer, coalition.propose]
when:
  any_text_matches_category: [medical_dosage, legal_advice, investment_advice]
then: escalate
explain: "Coordinate the task; leave the advice to a qualified person."
```

**An eval** scripts participants, their private vault contents and the outcome. Each participant MAY name a `role` declared by the pack. If omitted, the default is the first declared role whose abilities include both `offer` and `decide`; if no such role exists, the loader refuses the scenario with an explanatory error:

```yaml
scenario: three-people-one-booking
charter: "Find two hours next week when all three are free and book a room."
participants:
  - id: p1
    vault: { free: ["Tue 10-12", "Wed 14-16"], canary: "C-7Q2X" }
  - id: p2
    vault: { free: ["Wed 14-16", "Thu 09-11"], canary: "C-M41P" }
  - id: p3
    vault: { free: ["Wed 14-16"], canary: "C-0ZK9" }
expect:
  decision: { slot: "Wed 14-16" }
  canaries_leaked: 0
  max_messages: 60
```

**The loader rejects** a pack that declares a policy action other than allow, redact, block or escalate (quarantine acts on a participant, not a message, so it stays with the core); references a component outside the catalog; asks for vault access; points at a file outside its own folder; or changes any protocol schema rather than extending it. The core runs every example and eval in a pack through its own schemas as well as the pack's, so a pack cannot pass with data the core would refuse.

A pack MAY mark an extension property with `"x-private": true`. Such values belong in the member’s vault and MUST NOT be included in a transmitted `ext`. Viewer feed pack metadata includes only the pack’s `need` and `offer` extension schemas under `schemas`; private annotations remain visible to forms. Referenced schemas are bundled through the same closed registry used for validation, inlining sibling files and approved core ids with their `x-private` annotations, without exposing pack file paths. Cyclic or unresolvable references cause the loader to refuse the pack before installation. A viewer without a bound pack receives no pack metadata.

**Binding a pack to a Coalition.** A host installs packs from folders it is given and validates each with the loader; a pack that fails is not installed and the host reports the loader's reasons. A Coalition uses a pack only when its charter names it in `pack: {name, version}`, and only an installed pack with that exact name and version. The binding is fixed for the life of the Coalition: a new charter revision may not change `pack`. When a charter names a pack, the host applies it as follows, and nothing else changes:

| Key | At run time |
|---|---|
| `roles` | The roles the charter may use and what each may do. A member's message needs an ability its role grants; otherwise `not_authorized` |
| `vocabulary` | Words delivered to surfaces with each viewer's projection; never part of any signed payload |
| `schemas` | A pack adds fields to needs and offers only inside their `ext` object. The core schema validates the payload, then the pack's extension validates `ext`; failing it is `schema_invalid`. Without a bound pack, `ext` must be absent. A pack schema may reference only files in its own folder and the core schemas by their `https://coalitionkit.dev/schemas/` ids |
| `policies` | Checked deterministically at step (12) of the check order, after every core check and before the Steward: `block` is `pack_violation` with the policy id; `escalate` holds the message (it does not count), tells the sender it was held with the policy id, and asks the sender's person to review it, who may revise and resubmit; `redact` adds the fields the policy matched (for a text condition, each string field the text matched in) to the event's `scope.redact` before it is stored; `allow` changes nothing. The most severe matching action wins |
| `strategy` | The Gardener's allocation strategy and fairness settings for this Coalition |
| `task_templates` | Needs the Gardener may draft first from the charter |
| `views` | Component order per role and device for composed surfaces; components from the core catalog or the pack's catalog extension |
| `skills`, `lessons` | Skills are offered to every agent that joins (an MCP resource `coalition://{id}/skills` and the join reply). At Dissolve the host fills each lesson template from the log (placeholders: `goal`, `members`, `tasks`, `allocation`, `decisions`, `changes`, `policy_outcomes`, `duration`) and stores the results as skills, scoped no wider than the events they came from, listed in `skills_written`, and offered to agents that join later Coalitions bound to the same pack. A Coalition without lesson templates writes one generic lesson from the same placeholders |
| `mint` | Templates added to the Mint for this Coalition only; each template's tests run before a minted agent is enrolled |
| `compare` | Each seated person's agent asks the declared question beside its own questions, and the answer stays in that seat's vault. A seat whose own agent acts over MCP gives its values by writing the vault key `compare:<id>` (a list of strings) through `POST /v1/agent/vault`. After the offers the host compares each set with the PSI messages (`query`/`answer`, then `match` rounds chained by the first seat that holds values) over the elements `"<id>:<value>"`, and publishes one `coalition.observe` with `source: "document"` whose `content` is `{"common": 1, "set", "values", "compared"}` for `overlap` or `{"common": 1, "set", "count", "compared"}` for `count`. The exchanges between the vaults the host keeps use `reveal: overlap`; in `count` mode only the number leaves the host. With fewer than `min_seats` seats holding values nothing is published. Plans and results may use only the published values |
| `public` | Each seated person is asked the declared question; the answer is published once as a `coalition.observe` from that seat (`source: "chat"`, content `"<label>: <answer>"`). With `search: true` the answer joins that seat's web search words for `place` needs |
| `connectors` | Programs the operator runs out of process for this Coalition. A connector gets only a one-use invitation and joins like any business agent with a signed card; it never receives host settings, keys, tokens or access to the store or to vaults |

**Acceptance journey.** The optional `acceptance` key in `pack.yaml` is a relative path to a YAML file. `coalitionkit pack accept <folder> [--live] [--json]` drives an in-process host from Genesis through Dissolve. All structural objects forbid extra keys. Member roles must exist in the pack; member IDs are `p1` through `pN` in join order. Need indices are zero-based task-template or Gardener need indices. Offers are member messages validated against core and pack schemas. Exactly one distinguishing case is specified:

```yaml
goal: "<the sentence typed in Genesis>"
utc_offset_minutes: 60            # optional
members:                          # 2..12
  - role: <role id>
    vault: { <key>: <value>, canary: "<string>" }
    absent: false                 # optional; agent answers, owner must still approve commitments
businesses:                       # optional; business invitation and signed card
  - role: <role id>
    card: { name: "<display name>" }
offers:
  - member: p1
    need: 0
    offer: { ... }
expect:
  allocation: { 0: p1 }           # optional
  fairness: { max_share_ratio: 2 } # optional; plan objective scores
  commitments_signed_by_owner: true
  agent_only_yes_refused: true
  distinguishing:                # exactly one of these three
    minted_reading: { template: "<mint template name>", value: "<value>", changes_needs: [0] }
    # absent_answered: { member: p3, answer: yes }
    # business_holds: { business: 0, need: 0 }
  change:
    by: p2
    invalidates: [0]
    affected: [0]
    untouched: [1]
  policy_probe:
    by: p1
    type: coalition.offer        # or coalition.observe
    payload: { ... }
    outcome: block               # block | escalate | redact | allow
    policy_id: <id>
  dissolve:
    reason: completed
    lessons: 1                   # minimum number of skills_written
  canaries_leaked: 0
  max_messages: 200
```

Each assertion reports a named pass/fail step and reason. Canary scanning covers the log, every viewer's projection and replay, Steward inputs, agent channels and connector exchanges. Live member agents use the gateway and report calls, tokens, latency and cost; `--live` without `COALITIONKIT_META_API_KEY` reports `not run (no key)`.

**Strategy names.** `strategy.allocation` names one of the host's built-in strategies, and `strategy.fairness` may set only the keys that strategy reads:

| Name | What it does | Fairness keys |
|---|---|---|
| `auction` | Each task goes to the offer with the lowest cost plus a fairness weight times the bidder's share after winning (Contract-Net) | `weight` (0 to 10), `max_ratio` (hours per share unit, greater than 0), `minute_value` (whole number of at least 1, the value of a minute against money) |
| `match` | Reserved for a later version; not usable by packs in v0.1 (the host cannot read PSI overlaps) | none |
| `vote` | Reserved for a later version; not usable by packs in v0.1 (the host has no ballots) | none |

Any other name, or a fairness key the named strategy does not read, is refused when the pack is installed.

A pack never widens a scope, never reads a vault, never changes a core schema, and never sees another Coalition. The kit contains no pack: packs are data the host is given at run time.

## Conformance tests

An implementation claims conformance at one of four levels by passing every test at that level with the published runner: `coalitionkit conform --target <card-url> --level member`.

| ID | Test | Level |
|---|---|---|
| C-01 | Card declares the extension and carries a valid signature | Member |
| C-02 | Joins with an owner key and proof, receives the charter and acknowledges it | Member |
| C-03 | Every sent envelope validates against its schema and verifies; every `consent_sig` verifies against the owner key and fails against the agent key | Member |
| C-04 | Never addresses anyone outside the scope it was given | Member |
| C-05 | Sends no field a payload schema does not define | Member |
| C-06 | Answers queries only with yes, no or a cost, before the deadline | Vault |
| C-07 | Completes a PSI exchange that reveals only the overlap, reproducing `spec/vectors/psi.json`, and refuses `count` from a requester the charter does not name | Vault |
| C-08 | Leaks none of 20 planted canaries under scripted extraction attempts | Vault |
| C-09 | Assigns gap-free `seq` and a valid hash chain from the genesis hash under concurrent senders; every acknowledgement carries a verifying receipt; an edited tail entry and a truncated tail are each caught by the receipts a member kept | Host |
| C-10 | Rejects out-of-stage messages with `stage_mismatch`. Planning starts at the first host `query`, `propose` or `tension` naming an open task. A pending commitment can be withdrawn while its task is `decided`, which sends the task to `negotiating` and closes its consent request. Two-task scenario: while task A is back in `negotiating` (a refusal or ripple), `answer`, `match` and `offer` about A are accepted and `done` about A is `stage_mismatch`; at the same time task B is `committed`, so `done` about B is accepted and `answer` about B is `stage_mismatch` | Host |
| C-11 | Delivers nothing outside its scope, checked by an observing member; delivers a host-signed projection, never the sender's JWS, whenever a field is redacted for the recipient, and the original otherwise; a replay mixing originals and projections verifies the chain and the kept receipts through the projections' `prev_hash` and `hash`; an acknowledgement and its duplicate leak no redacted field and give a sender outside the scope only the receipt | Host |
| C-12 | Calls the Steward before delivering proposals and honors a block | Host |
| C-13 | Returns the original acknowledgement for a duplicate `event_id` from the same sender with the same digest, and `duplicate_mismatch` (with an empty `detail`) for another sender or other bytes; the duplicate acknowledgement has the same scope-filtered form as the first | Host |
| C-14 | Refuses an envelope whose `sender` differs from the authenticated connection | Host |
| C-15 | Records the first answer per (subject kind, id, revision, decider) and refuses a stale revision with `stale_subject`; with two deciders answering concurrently it records both and decides only after the second consent; a refusal sends the tasks to `negotiating`; two deciders consenting to different tension options decide nothing and send the tasks to `negotiating`; a decision after `decision_deadline` is `deadline_exceeded`, and an undecided subject at its deadline returns its tasks to `negotiating` with no commitment; a replan supersedes the task's active commitment and needs a new commitment and a fresh owner approval; a second answer from the same decider is not recorded (`not_authorized`); keeps a consent open across a disconnect; refuses a decision whose `consent_sig` the pinned owner key does not verify | Host |
| C-16 | Gives every derived output the narrowest scope of its sources: the intersection of the resolved principal sets at derivation time, roles resolved to the members holding them then, `self` resolved to the source sender's owner, an empty intersection becoming `host`, any unprojected source with a redaction list making the output `host`, projected sources contributing none; reproduces `spec/vectors/scope.json` | Host |
| C-17 | Renders every catalog component from AG-UI snapshots and deltas | Surface |
| C-18 | Shows a consent request and records only the person's own answer | Surface |
| C-19 | Shows nothing outside the viewer's scope, from the first snapshot on | Surface |
| C-20 | Applies the authorization matrix: each row of Target authorization is rejected with `not_authorized` (or `not_a_decider`) when the sender is the wrong party or the object is not its own, even where the scope allows it; host-only types are rejected from members; a first-time `join` from an invited participant is accepted (not `unknown_participant`); a `match` round for another `task_id`, or for a task not `negotiating`, is rejected; a `commit` reusing a `commitment_id` is `not_authorized` | Host |
| C-21 | Counts a member's offers and commitments only after it accepted the current charter revision and suspends its open commitments on a new revision | Host |

The runner prints a signed report that implementers may publish with their release.
