# Coalition Protocol v0.1 (draft)

## Status, conformance language and versioning

This is a working draft of Coalition Protocol v0.1, an extension to A2A for sessions shared by many agents. It will change in response to implementers until v1.0 freezes it.

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
| Acknowledgement | Two such parts, in order: the accepted envelope, then its `coalition.receipt` |
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
- Object identifiers the host mints (needs, tasks, plans, tensions, commitments) are ULIDs. Identifiers a participant mints (`offer_id`, `query_id` answered by it, `match_id`) are strings of 1 to 128 characters.

### Idempotency is authenticated

The host looks up every submission by (`coalition_id`, `event_id`) before it does anything else that depends on the content. It then compares the authenticated sender and the *submission digest*, the SHA-256 of the JCS form of the resubmitted envelope without its host fields (`seq`, `ts`, `prev_hash`; `sig` stays in):

| Lookup finds | Same authenticated sender and same digest | Result |
|---|---|---|
| Nothing | n/a | Process normally |
| An accepted event | Yes | Return the original acknowledgement (the same accepted envelope and the same receipt); append nothing |
| An accepted event | No (other sender, or other bytes) | Reject with `duplicate_mismatch` |

`duplicate_mismatch` discloses nothing about the original: the same answer, with an empty `detail`, whichever of the two differed and whether or not the sender could ever see the original. A sender that really wants to change a message sends it under a new `event_id`.

### Acknowledgements and receipts

The host acknowledges every accepted envelope with the accepted envelope (now carrying `seq`, `ts` and `prev_hash`) and a host-signed `coalition.receipt` with payload `{coalition_id, seq, head_hash}`, where `head_hash` is the SHA-256 of the JCS form of the accepted envelope at `seq`, which is also the value the next envelope's `prev_hash` must hold. A receipt is scoped to its recipient, signed with the host key and never appended to the log. The sender SHOULD keep every receipt. A host MUST NOT acknowledge an event it has not committed.

### The authenticated log boundary

The genesis: `prev_hash` of seq 1 is the SHA-256 (lowercase hex) of the JCS form of `{"coalition_id", "host_card_url", "created_at"}`, where `host_card_url` is the host's card URL and `created_at` is the RFC 3339 time the host created the Coalition. `created_at` is also carried in every `coalition.charter`, so a member can recompute the genesis hash.

A reader that holds the whole log, or a replay in which events outside its scope are replaced by stubs `{seq, prev_hash, hash}` (the stub's `hash` being the SHA-256 of the JCS form of the original), checks four things: seq is gap-free from 1; seq 1 links to the genesis hash; each `prev_hash` equals the hash of the entry before it; and, for every receipt it kept, the log reaches that receipt's `seq` and the entry there hashes to the receipt's `head_hash`. The first three catch gaps and edits inside the log. Only the receipts catch an edited last entry, an edited tail whose later `prev_hash` values were recomputed, and a truncation: a host that cuts the log back, or rewrites its tail, cannot produce a log that fits a receipt it signed earlier. A member can detect only what its own receipts cover.

### Projections

Anything delivered with a field redacted, or projected for a particular viewer, is a *projection*: an envelope of type `coalition.projection` signed by the host key. It never carries the sender's original JWS and is never appended to the log. Its payload is:

| Field | Meaning |
|---|---|
| `source` | `event_id`, `seq`, `type` and `on_behalf_of` of the logged event it is derived from |
| `payload` | The source payload after redaction or per-viewer projection. It is not validated against the source type's schema, because redaction removes required fields |
| `redacted` | Optional list of the `payload.` paths removed |

Recipients verify a projection against the host key they pinned, never against the sender's key. The host delivers the *original* envelope only when no field is redacted for that recipient and the event is not viewer-specific; otherwise it delivers a projection. `scope.redact` applies to every recipient except the host and the Steward, so any event with a non-empty `redact` is delivered to everyone else as a projection. A per-member `coalition.propose` (each member sees only its own assignments) is likewise a projection. The projection's own `scope` is the recipient.

## Message types

Eighteen types in v0.1: ten that members, vaults and edges send and eight that only the host sends. Payload fields listed are the required ones; each type has its own JSON Schema in `schemas/coalition/v0/`.

| Type | From, to | Required payload fields | Notes |
|---|---|---|---|
| `coalition.charter` | Host to members | `goal`, `roles`, `rules`, `deadline`, `deciders`, `revision`, `created_at`; optional `pack`, `budget`, `count_trusted` | `deciders` (non-empty) are the participants who decide plans; an updated charter carries `revision` + 1 and members re-accept it |
| `coalition.join` | Member to host | `card_url`, `owner_key`, `owner_proof`, `roles_requested`, `surfaces`, `vault` (`local` or `hosted`) | `owner_key` is an Ed25519 JWK; `owner_proof` binds it to the participant (see Owner authority). The host replies with granted roles |
| `coalition.leave` | Member to host | none (a reason is optional and never required) | Withdraws the member's open offers |
| `coalition.observe` | Edge to host | `source` (`voice`, `camera`, `chat`, `device`, `document`), `content`, optional `evidence_ref` | Scoped to who may see the source |
| `coalition.need` | Host to members | `need_id`, `description`, `requirements`, `window` | Publishing a need creates a task with the same ID in status `open` |
| `coalition.offer` | Member to host | `offer_id`, `target` (a need or task), `capacity`, `cost`, `valid_until` | `cost` has `minutes`, `money` and `effort`; no free text |
| `coalition.query` | Host to vault | `query_id`, `kind` (`feasible`, `cost`, `availability`), `subject`; optional `deadline_ms` | `deadline_ms` defaults to 10,000 |
| `coalition.answer` | Vault to host | `query_id`, `result` (`yes`, `no` or a cost) | The only thing a vault ever returns |
| `coalition.match` | Vault to vault, relayed by the host | `match_id`, `peer`, `round` (`setup`, `request`, `response`), `blob`, `reveal` (`overlap` or `count`) | The host relays opaque blobs and cannot read them (see Private set intersection) |
| `coalition.propose` | Host to members | `proposal_set_id`, `plans` (each with `plan_id`, `revision`, assignments and objective scores) | Each member sees only its own assignments (a projection) |
| `coalition.tension` | Host to deciders | `tension_id`, `revision`, `options`, `tradeoffs`, `deciders` |  |
| `coalition.decide` | Member to host | `subject`, `choice`, `consent` (true or false), `decided_at`, `consent_sig` | `consent_sig` is by the owner key |
| `coalition.commit` | Member to host | `commitment_id`, `task_id`, `status` (`pending` or `withdrawn`); optional `revision` | Never `approved`: approval is an owner-signed `coalition.decide` |
| `coalition.ripple` | Any participant | `change`, `invalidates` (task IDs) | Scoped like the change it reports |
| `coalition.done` | Member to host | `task_id`, `evidence` (each with `kind`, `ref`, `verified_by`) |  |
| `coalition.dissolve` | Host to members | `reason` (`completed`, `deadline`, `cancelled`, `budget`), `skills_written` | Final message of a Coalition |
| `coalition.projection` | Host to members | `source`, `payload`; optional `redacted` | Host-signed; see Projections |
| `coalition.receipt` | Host to the sender | `coalition_id`, `seq`, `head_hash` | Host-signed; see Acknowledgements and receipts |

Errors travel as `coalition.error` with a `code`, a `detail` and the `ref` of the event they answer (see Errors). `coalition.error` is a payload type the host sends but not one of the eighteen.

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

The host assigns revisions. An object starts at revision 1 and the revision goes up by 1 on every change to it. The producers expose the current revision: `propose` in each plan's `revision`, `tension` and `charter` in `revision`, and `commit` through the consent request and the projection delivered to its decider (a member omits `revision` when it creates a commitment, and gives the revision it is withdrawing when it withdraws one). Recording a decision compares the decision's revision with the current revision atomically, in the same transaction that records it. Any other revision, older or newer, fails with `stale_subject`. A change to the subject supersedes every pending consent request for an older revision.

### Owner authority

Agent authority and owner authority are separate.

- **At join**, the member sends `owner_key`, an Ed25519 JWK `{kty: "OKP", crv: "Ed25519", x, kid}`, and `owner_proof`: a compact JWS (detached payload) made with the owner key over the JCS form of `{"coalition_id", "participant", "card_url", "owner_key"}`, where `participant` is the envelope's `on_behalf_of`. The host verifies the proof under the key it carries, checks that the key differs from the agent key, and pins it for that participant. Join is refused with `schema_invalid` or `bad_signature` otherwise.
- **Every `coalition.decide`** carries `decided_at` and `consent_sig`: a compact JWS (detached payload) by the OWNER key over the JCS form of `{"coalition_id", "subject", "choice", "consent", "decided_at"}`. The host verifies it against the pinned owner key of the participant in `on_behalf_of`; a failure is `bad_signature`. The agent's envelope signature alone never makes a decision count, and a `consent_sig` made with the agent key fails.
- **Through MCP**, the server's hosted owner key signs a decision only after the person answers an MCP elicitation for that exact subject and revision (see The CoalitionKit MCP server).

## Target authorization

A message must pass two independent tests: the scope rules (who may see what) and the authorization matrix below (who may send which type about which objects). Being able to see an object, or being named in a scope, never authorizes an action on it. The host checks the matrix after the stage and task-status check and before it applies the message. A failure answers `not_authorized`, except for `decide`, which answers `not_a_decider`.

| Type | Who may send | About which objects |
|---|---|---|
| `join` | An agent with a valid signed card that is not yet a member | Itself; `on_behalf_of` is its owner |
| `leave` | A member | Itself only |
| `observe` | An Edge, or a member | Evidence it holds; its scope may be no wider than who may see the source |
| `offer` | A member | A need or task that is `open` or `negotiating` and visible to the sender. The offer counts only once the sender has accepted the current charter revision |
| `answer` | The vault of the participant the query was addressed to | Exactly one open `query_id`, once. A second answer is `not_authorized`; a late one is `deadline_exceeded` |
| `match` | One of the two parties of the exchange | Its own `match_id`, addressed to the `peer` fixed by `setup`; `setup` and `request` only from the requester, `response` only from the responder, each round once and in order |
| `commit` (create, `pending`) | The agent of the assignee's owner | A task that the decided plan assigns to its owner and that is `decided`; one active commitment per task |
| `commit` (`withdrawn`) | The agent that created it | Its own commitment |
| `decide` | A decider named for the subject: for `plan`, the charter's `deciders`; for `tension_option`, the tension's `deciders`; for `commitment` and `task`, the owner of the assignee; for `charter`, each member for itself | The named subject at its current revision; one answer per decider and revision. Approval of a commitment exists only as an owner-signed `decide` |
| `done` | The agent of the assignee | A task assigned to its owner whose commitment is approved (task `committed`) |
| `ripple` | A member | Tasks visible to the sender only; every ID in `invalidates` must be one |
| `charter`, `need`, `query`, `propose`, `tension`, `dissolve`, `projection`, `receipt` (and `error`) | The host only | Rejected from any member, vault or edge |

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

An empty intersection becomes `host`. Redaction lists are unioned across the sources. The derived scope is written as `coalition` when every source is `coalition`, as `roles` when every source lists the same roles, and otherwise as `participants` with the sorted intersection (or `host` when it is empty). The reference function is `resolve_narrowest` in `coalitionkit_contracts`; the cases are in `spec/vectors/scope.json`.

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
| `open` | `offer`, `ripple` | `negotiating` when the host starts planning it |
| `negotiating` | `answer`, `match`, `offer`, `ripple` | `proposed` when a plan or tension covering it passes the Steward |
| `proposed` | `decide` (plan, tension option or task), ripple | `decided` when every named decider has consented |
| `decided` | `commit` (`pending`), `decide` (commitment or task), `ripple` | `committed` when the assignee's owner approves the commitment |
| `committed` | `done`, `commit` (`withdrawn`), `ripple` | `done` |
| `done`, `withdrawn` | Nothing | Terminal |

The host also sends `query`, `propose` and `tension` about a task in the statuses where they apply (`negotiating` for queries and proposals; `negotiating` or `proposed` for tensions). Any refusal in `proposed` or `decided`, a withdrawn commitment, or a ripple that invalidates the task sends it back to `negotiating`. A task not `done` when the Coalition dissolves is closed as `withdrawn`; a `done` sent in Dissolve is `stage_mismatch`.

**Rules**

1. Members MUST treat `seq` as the total order and MAY reorder their local view by it.
2. A refused consent, a withdrawn commitment or a ripple sets the affected tasks back to `negotiating`; the Coalition keeps its stage. Only when every open task is back to `negotiating` does the Coalition itself return to Negotiate.
3. The host MAY send `coalition.dissolve` from any stage on cancellation, deadline or budget exhaustion.
4. Only a decider named for the subject may send `coalition.decide` for it (see Target authorization).
5. **Decisions are per decider.** The first answer wins per (Coalition, `subject.kind`, `subject.id`, `subject.revision`, decider). A later answer from the same decider for the same key is not recorded and gets `not_authorized`. A subject is *decided* when every named decider has consented. Any refusal sends the subject's tasks back to `negotiating`. Answers from different deciders arrive in `seq` order, are all recorded, and the last consent decides the subject.
6. A decision names the revision of the subject it answers and the host compares it atomically as described under Subjects and revisions; a decision on any other revision is refused with `stale_subject`.
7. A commitment made by an agent for an absent owner stays `pending` until that owner's own `coalition.decide`, with the owner's `consent_sig`, approves it. The member's `commit` carries `pending` or `withdrawn`; `approved` is a host-side state reached only through that decision.
8. Delivery is at least once; receivers deduplicate by `event_id`.

### Charter acceptance

A member accepts a charter with `coalition.decide` on a subject of kind `charter` at the charter's current `revision`, owner-signed like any decision. It is allowed in every stage before Dissolve. A member's offers and commitments count only after it has accepted the current charter revision. A new charter revision suspends the member's open commitments (a host-side flag) until the member accepts the new revision; a suspended commitment cannot be reported `done`. An answer that refuses the charter leaves the member without counting offers or commitments.

## Errors, timeouts and retries

Errors are messages, never silence. Every rejected envelope gets a `coalition.error` scoped to its sender, and a true duplicate gets its original acknowledgement back. When a rejected envelope has no valid `event_id`, `ref` is a ULID the host mints for the purpose.

| Code | Meaning | Sender should |
|---|---|---|
| `schema_invalid` | The envelope or payload fails its JSON Schema | Fix and resend with a new `event_id` |
| `bad_signature` | The envelope signature does not verify against the sender's pinned card key, or a `consent_sig` or `owner_proof` does not verify against the owner key | Re-sign; check key rotation |
| `sender_mismatch` | `sender` or `on_behalf_of` differs from the authenticated connection | Drop the message |
| `unknown_participant` | The sender has not joined, or has left | Join first |
| `extension_not_activated` | Coalition data arrived on a call without the `A2A-Extensions` header | Resend with the header |
| `stage_mismatch` | The type is not accepted in the current stage, or the task is not in the right status | Wait for the stage, or drop the message |
| `scope_violation` | The scope names someone the sender may not address, or is wider than its sources | Narrow the scope |
| `not_authorized` | The sender may not send this type about this object (see Target authorization) | Drop the message |
| `not_a_decider` | A decision from someone not named for the subject | Drop the message |
| `stale_subject` | The decision answers a revision other than the subject's current one | Read the current revision and decide again |
| `duplicate_mismatch` | The `event_id` is already taken in this Coalition by another sender or by different bytes; `detail` is empty | Send under a new `event_id` |
| `steward_blocked` | The Steward refused it; `detail` gives the policy ID | Revise, or ask a human |
| `deadline_exceeded` | The answer arrived after its query's deadline | Nothing; the sender was counted as abstaining |
| `rate_limited` | The sender exceeded its rate | Back off as told in `detail.retry_after_ms` |
| `budget_exhausted` | The Coalition's model budget is spent | Nothing; the Coalition continues without model calls |
| `pack_violation` | A pack policy forbids the action | Revise |

**Check order.** The host checks in this order and stops at the first failure: (1) `extension_not_activated`; (2) `sender_mismatch`, from `sender`, `on_behalf_of` and `event_id`, which it reads before schema validation; (3) the idempotency lookup, answering a replay or `duplicate_mismatch`; (4) `rate_limited`; (5) `schema_invalid`; (6) `unknown_participant`; (7) `bad_signature`, including `consent_sig`; (8) `stage_mismatch`, stage then task status; (9) `not_authorized` or `not_a_decider`; (10) `scope_violation`; (11) `stale_subject`, at recording time inside the transaction; (12) `pack_violation`, then `steward_blocked`. `deadline_exceeded` and `budget_exhausted` apply where their conditions arise.

**Timeouts**: each `coalition.query` MAY carry `deadline_ms`; when it is missing the deadline is 10,000 ms (a pack may change the default), and silence counts as abstaining. Decisions carry a deadline in their tension or proposal.

**Retries**: senders retry transport failures with exponential backoff and jitter, reusing the same `event_id` and the same bytes. The host retries delivery to a member up to a configured limit, then marks it unreachable and notifies its owner through another surface.

## Private set intersection (PSI)

`coalition.match` carries a two-party PSI between two vaults. The host relays; it cannot read a blob.

**Scheme.** ECDH-PSI over the ristretto255 group (RFC 9496), with the group order *L* and a fresh secret scalar per exchange. `H(x)` maps an element to the group with `hash_to_group` of the RFC 9380 suite `ristretto255_XMD:SHA-512_R255MAP_RO_` (`expand_message_xmd` with SHA-512 to 64 bytes, then the RFC 9496 one-way map) over the element's bytes `x` (the vault's canonical encoding of the item, up to 4,096 bytes). The domain separation tag binds the exchange: `DST = "CoalitionKit-PSI-v0:" || hex(SHA-256(JCS({"coalition_id", "match_id", "requester", "responder"})))`, where `requester` is the `on_behalf_of` of the sender of `setup` and `responder` is its `peer`. The order of the pair is part of the binding; swapping the roles gives different points.

**Rounds**

| Round | Sent by | `blob` |
|---|---|---|
| `setup` | Requester, with `peer` = responder and the chosen `reveal` | A frame header only: the requester's element count *n* |
| `request` | Requester | A frame of *n* points `H(x_i)^a`, in a uniformly shuffled order (*a* is a random scalar in 1..*L*-1) |
| `response` | Responder | Two frames in order: *echo*, the request points raised to *b* (random in 1..*L*-1), then *own*, the responder's points `H(y_j)^b` in a uniformly shuffled order |

**Frame.** A frame is a 32-bit big-endian element count followed by that many 32-byte canonical ristretto255 encodings. A blob is the unpadded base64url (RFC 4648 section 5) encoding of the concatenated frames: one header for `setup`, one frame for `request`, two frames for `response`. A receiver rejects a blob with a wrong length, a count above 1,024, a non-canonical or identity element, a duplicate element in a list, or a count that differs from the `setup` count. The schema limits the encoded length to 87,392 characters.

**Limits and reveal.** Each side contributes at most 1,024 elements. For `reveal: overlap` the responder returns *echo* in the order it received; the requester raises each *own* point to *a*, finds which echo points match, and learns exactly those elements of its own set. For `reveal: count` the responder shuffles *echo* independently, so the requester learns only the size of the intersection. In both cases the requester also learns the responder's set size, the responder learns the requester's set size, and the host learns both sizes. The result reaches the requester only; a responder that wants the overlap runs a second exchange with the roles swapped. A responder that declines sends nothing and the requester treats silence as abstaining after the deadline.

**Threat model.** v0.1 PSI is secure against semi-honest (honest-but-curious) participants only. If both vaults follow the protocol, neither vault nor the relaying host learns any element outside the intersection; the host learns the set sizes. A malicious requester in `count` mode could blind each element with a different scalar and so learn which elements matched, not only how many. Therefore a vault MUST accept `reveal: count` only from a requester that the charter names in `count_trusted`, and otherwise refuse with `not_authorized`; `overlap` is the default and is always available to a requester the vault's own policy accepts. A zero-knowledge proof that one blinding scalar was used for all request points is deferred to v0.2. Low-entropy elements can be guessed by the peer by hashing candidates, so a vault decides which of its sets it will put into an exchange at all.

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

**Resources**: `coalition://{id}/charter`, `coalition://{id}/my-tasks` and `coalition://{id}/log?since={seq}`, each filtered to the caller's scopes. The 2026-07-28 spec is stateless, so every read is authorized on its own; nothing carries over from an earlier call. Tool results are rebuilt from an allowlist of fields, because hosts copy structured content into the text the model reads. A log read returns originals only where nothing is redacted for the caller, projections elsewhere, and stubs for events outside the caller's scope.

**MCP Apps**: one versioned view, `ui://coalitionkit/surface-v1.html`, renders the participant's live surface inside the host, so a Claude or ChatGPT user sees the same screen as a web user. The Coalition ID travels as tool data, never in the URI, because hosts cache views by URI; a breaking change to the view ships under a new URI. The view is one bundled HTML file under the default closed CSP, every tool it calls is authorized again on the server, and every tool also returns readable text for hosts that render no views.

**Auth**: MCP's OAuth-based authorization; each access token maps to exactly one participant. The server holds two hosted keys for that participant and never a shared key: the agent key signs envelopes, and the hosted owner key signs consent.

**Writes need a person**: `decide`, `approve_commitment` and `accept_charter` ask the person through MCP elicitation inside the tool call (multi-round tool results in the 2026-07-28 spec). The server's hosted owner key signs the `consent_sig` only after the person has answered an elicitation for that exact subject and revision, and records only the answer given there. For `approve_commitment` and `accept_charter`, whose input carries no revision, the server reads the subject's current revision when it builds the elicitation, shows it to the person, and signs for exactly that revision; if the revision changes before the answer, the elicitation is void and the host's `stale_subject` check stands. A confirmation flag in the tool's arguments is never trusted, because a model or an MCP App view can set it. `commit` and `report_ripple` need no elicitation: neither carries owner authority.

## Surfaces: AG-UI and A2UI

Surfaces use AG-UI 1.0 for the live stream and A2UI v0.9.1 (the current stable release; messages carry `"version": "v0.9"`) for the components. A2UI v1.0 is a release candidate, and moving to it changes behaviour as well as names (deletion, themes, duplicate surfaces), so v0.1 stays on v0.9 and the move gets its own ADR.

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

**The v0.1 catalog** is a closed custom catalog, `coalitionkit/v0_9`; renderers refuse any other catalog ID.

| Component | Shows | Key props |
|---|---|---|
| Card | One object with a title and fields | `title`, `fields`, `status`, `provenance` |
| List, Table | Several objects | `items` or `rows`, `columns`, `sort` |
| Timeline | Tasks and commitments over time | `items` with `start`, `end`, `assignee` |
| Form, Choice | Input from a person | `fields` or `options`, `submit_event` |
| ApprovalButton | A one-tap consent | `subject`, `label`, `consequence` |
| PlanCompare | Plan universes side by side | `plans`, `objectives` |
| TensionCard | A conflict and its trade-offs | `options`, `tradeoffs`, `deciders` |
| Progress, Gauge | A value against a goal or range | `value`, `min`, `max`, `unit` |
| Map | Places | `points`, `areas` |
| MediaWithMasks | An image or video frame with SAM masks | `media_ref`, `masks`, `labels` |
| Evidence | Proof that a task was done | `kind`, `ref`, `verified_by` |
| DecisionLog | Who decided what, and why | `entries` |
| WiringOverlay | The protocol message behind any element | `event_ref` |

Every component has an accessible label, a right-to-left layout and four device variants (wide, compact, message, voice). The host validates every tree before sending it: known components only, one root, no orphans or cycles, at most 500 components and a depth of 24, no HTML in props, and every number bound to the event it came from. Renderers show values as text only. A tree that fails validation is replaced by the fixed layout.

## Discipline Pack format

A pack is a folder of data the loader validates before a Coalition can use it. A pack that fails validation never loads, and the loader's report says which rule it broke.

| Key in `pack.yaml` | Required | Meaning |
|---|---|---|
| `name`, `version` | yes | Unique name and semantic version |
| `core` | yes | The range of core versions it works with, such as `>=0.1,<0.2` |
| `roles` | yes | Role IDs and what each may do: `charter`, `offer`, `decide`, `decide_own`, `commit` |
| `vocabulary` | no | Words shown on screens for core objects (task, resource, need) |
| `schemas` | no | JSON Schemas that extend the core payloads for needs, offers, tasks and resources |
| `policies` | no | Steward policy files |
| `skills` | no | SKILL.md files loaded by agents that join |
| `views` | no | Component order per role and device |
| `mint` | no | Extra Mint templates, each with its own tests |
| `connectors` | no | MCP servers the pack needs, run out of process |
| `strategy` | no | Allocation strategy and fairness settings |
| `evals` | yes | At least one scripted scenario |

**A policy** is checked deterministically before the Steward's model audit:

```yaml
id: no-regulated-advice
applies_to: [coalition.observe, coalition.offer, coalition.propose]
when:
  any_text_matches_category: [medical_dosage, legal_advice, investment_advice]
then: escalate
explain: "Coordinate the task; leave the advice to a qualified person."
```

**An eval** scripts participants, their private vault contents and the outcome:

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
| C-10 | Rejects out-of-stage messages with `stage_mismatch`. Two-task scenario: while task A is back in `negotiating` (a refusal or ripple), `answer`, `match` and `offer` about A are accepted and `done` about A is `stage_mismatch`; at the same time task B is `committed`, so `done` about B is accepted and `answer` about B is `stage_mismatch` | Host |
| C-11 | Delivers nothing outside its scope, checked by an observing member; delivers a host-signed projection, never the sender's JWS, whenever a field is redacted for the recipient, and the original otherwise | Host |
| C-12 | Calls the Steward before delivering proposals and honors a block | Host |
| C-13 | Returns the original acknowledgement for a duplicate `event_id` from the same sender with the same digest, and `duplicate_mismatch` (with an empty `detail`) for another sender or other bytes | Host |
| C-14 | Refuses an envelope whose `sender` differs from the authenticated connection | Host |
| C-15 | Records the first answer per (subject kind, id, revision, decider) and refuses a stale revision with `stale_subject`; with two deciders answering concurrently it records both and decides only after the second consent; a refusal sends the tasks to `negotiating`; a second answer from the same decider is not recorded (`not_authorized`); keeps a consent open across a disconnect; refuses a decision whose `consent_sig` the pinned owner key does not verify | Host |
| C-16 | Gives every derived output the narrowest scope of its sources: the intersection of the resolved principal sets at derivation time, roles resolved to the members holding them then, `self` resolved to the source sender's owner, an empty intersection becoming `host`, redaction lists unioned; reproduces `spec/vectors/scope.json` | Host |
| C-17 | Renders every catalog component from AG-UI snapshots and deltas | Surface |
| C-18 | Shows a consent request and records only the person's own answer | Surface |
| C-19 | Shows nothing outside the viewer's scope, from the first snapshot on | Surface |
| C-20 | Applies the authorization matrix: each row of Target authorization is rejected with `not_authorized` (or `not_a_decider`) when the sender is the wrong party or the object is not its own, even where the scope allows it; host-only types are rejected from members | Host |
| C-21 | Counts a member's offers and commitments only after it accepted the current charter revision and suspends its open commitments on a new revision | Host |

The runner prints a signed report that implementers may publish with their release.
