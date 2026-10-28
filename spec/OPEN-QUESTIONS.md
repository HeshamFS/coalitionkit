# Open questions and schema choices (Coalition Protocol v0.1)

Where the spec leaves a field's inner shape open, the schemas use the smallest shape that works.
Each choice is listed here. Every choice below is mirrored in `spec/schemas/coalition/v0/*.json`
and in `packages/contracts`. Revision R1 applied decisions 1 to 13 of the spec review; revision R2 applied the ten major findings of the second review (rows and sections marked R2).

## Choices made

| # | Area | Choice | Why |
|---|---|---|---|
| 1 | Signature form | `sig` is a compact JWS with a **detached payload**: `<protected>..<signature>`. The verifier rebuilds the payload (JCS of the envelope without `sig`, `seq`, `ts`, `prev_hash`). Protected header is exactly `alg: EdDSA`, `typ: JOSE`, `kid`, written in JCS form. `consent_sig` and `owner_proof` use the same form over their own payloads. | Avoids carrying the payload twice and a payload that can disagree with the envelope. Now stated in the spec. |
| 2 | Integer range | Every integer is limited to 0..2^53-1 in the schemas and models (`seq` and `revision` from 1). | `rfc8785` refuses larger integers. Now stated in the spec. |
| 3 | `coalition.error` | `error.json` is the payload schema for type `coalition.error`: `code` (now 16 codes, with `duplicate_mismatch` and `not_authorized`), `detail`, `ref`. Not one of the eighteen types. | |
| 4 | Error `detail` | Object, all keys optional: `message`, `policy_id`, `retry_after_ms`. `duplicate_mismatch` uses an empty `detail`. | |
| 5 | Scope | Only `audience` is required; `audience: participants` needs a non-empty `participants`, `audience: roles` a non-empty `roles`; `redact` entries start with `payload.`; lists are unique. | |
| 6 | Common types | `id` = string, 1 to 128 characters. **Changed:** object IDs the host mints (need, task, plan, tension, commitment) and every subject `id` are ULIDs. `offer_id`, `query_id`, `match_id` stay free strings. | Subject references use ULIDs (decision 6). |
| 7 | `charter` | **Changed:** `deciders` is required and non-empty; `version` is renamed `revision` and is required; `created_at` is required (input of the genesis hash); optional `count_trusted` (participants a vault may accept as `count` requester). | Decisions 5, 6, 9, 11, 12. |
| 8 | `join` | **Changed:** adds required `owner_key` (Ed25519 JWK with `kid`); `owner_proof` is a detached compact JWS by the owner key over JCS of `{coalition_id, participant, card_url, owner_key}`. | Decision 3. |
| 9 | `leave` | No required field; optional `reason`. | |
| 10 | `observe` | `content` is a string (may be empty); `evidence_ref` is an ID. | |
| 11 | `need` | `need_id` is a ULID; `requirements`: list of non-empty strings; `window`: `{start, end}`. | |
| 12 | `offer` | `target`: `{kind: need or task, id (ULID)}`; `capacity` >= 1; `cost` with all three fields; `valid_until`. | |
| 13 | `query` | `deadline_ms` is optional, default 10,000. **R2:** optional `task_id` (ULID); the first host query naming an open task starts its planning. | A4, H1. |
| 14 | `answer` | `result` is exactly one of `"yes"`, `"no"` or a `cost` object. | |
| 15 | `match` | **R2:** adds required `task_id` (ULID, repeated in every round, not in the PSI context digest). Adds required `peer`; `blob` is unpadded base64url, at most 94,000 characters (the largest response at 1,024 elements per side is 93,068). | Decision 9. |
| 16 | `propose` | **R2:** required `decision_deadline` (RFC 3339, absolute). `plan_id` ULID, `revision` required; assignments use ULID `task_id`. `objective_scores` is an open map. | |
| 17 | `tension` | **R2:** required `task_ids` (non-empty, unique ULIDs) and `decision_deadline`. `tension_id` ULID, `revision` required. | Decision 6. |
| 18 | `decide` | **Changed:** `subject` is the shared shape (five kinds); adds required `decided_at` and `consent_sig`. | Decisions 3, 6, 11. |
| 19 | `commit` | **R2:** the member mints `commitment_id` (ULID) on create. `status` is `pending` or `withdrawn`; IDs are ULIDs; `revision` optional (omitted on create, the revision withdrawn on withdraw). | A6, decision 6. |
| 20 | `ripple` | `invalidates`: unique list of task ULIDs. | |
| 21 | `done` | `task_id` ULID; `evidence` entries with three required strings. | |
| 22 | `dissolve` | `skills_written`: list of IDs. | |
| 23 | Formats | `date-time` and `uri` are asserted by the validator; the models check the same. Date-times stay strings so signed bytes never change. | |
| 24 | Strictness | Models are strict: no coercion, no explicit `null`. | |
| 25 | Shared definitions | `common.json` holds `$defs`: `id`, `ulid`, `cost`, `window`, `target`, `budget`, `datetime`, `revision`, `money`, and now `subject`, `ed25519_jwk`, `detached_jws`, `sha256_hex`. | |
| 26 | New: `projection` | `{source: {event_id, seq, type, on_behalf_of, prev_hash, hash}, payload (open object), redacted?}` (**R2:** `prev_hash` and `hash` make a projection a verifiable stub), host-signed, never logged. | Decision 1. I added `type` and `on_behalf_of` to `source` so a recipient can interpret `payload`. |
| 27 | New: `receipt` | `{coalition_id, seq, head_hash}`, host-signed, never logged. `head_hash` is the SHA-256 of the JCS form of the accepted envelope at `seq`. | Decision 12. |
| 28 | Host-originated envelopes | `sender` is the host card URL, `on_behalf_of` is the literal `host`, signed with the host key. | The spec did not say who signs host messages. |

## Ambiguities recorded by lane 0 (A1 to A10)

- **A1. Placeholder domain.** Resolved: `https://coalitionkit.dev/ext/coalition/v0` and `https://coalitionkit.dev/schemas/coalition/v0/` everywhere; no placeholder remains.
- **A2. Charter deciders.** Resolved: `deciders` is a defined, required field of the charter.
- **A3. `approve_commitment` and revisions.** Resolved: the MCP server reads the current revision when it builds the elicitation, shows it, and signs for exactly that revision; a change before the answer voids the elicitation.
- **A4. `deadline_ms`.** Resolved: optional, default 10,000.
- **A5. Where a revision comes from.** Resolved: the host assigns revisions (1, then +1 per change); `propose`, `tension` and `charter` carry them, `commit` exposes it through the consent request and the projection to its decider.
- **A6. `commit` status `approved`.** Resolved: members send only `pending` or `withdrawn`; `approved` is a host-side state reached only through an owner-signed `decide`.
- **A7. Error `ref` without an event ID.** Resolved: the host mints a ULID for `ref`.
- **A8. Stage table versus task rule.** Resolved: task status governs all task messages from Gather to Live; the stage table covers Coalition-level messages only.
- **A9. Dissolve stage.** Resolved: `done` in Dissolve is `stage_mismatch`; tasks not done at dissolve close as `withdrawn`.
- **A10. `type` pattern versus the types.** Resolved as a rule: the envelope pattern accepts any `coalition.*` name; an unknown type is rejected at payload validation. The spec now says eighteen types plus `coalition.error`.

## Review round 2 (R2): the ten major findings

| # | Finding | Decision |
|---|---|---|
| R2-1 | Redaction provenance loss | Accepted. A derived output from a source with `redact` is `host`-only unless built from its redacted projection (`ScopeSource.projected`); a derived scope never carries `redact`. |
| R2-2 | Acknowledgement scope bypass | Accepted. The acknowledgement is the original, a projection, or only the receipt, by `delivery_form`; duplicates use the same form. |
| R2-3 | Unverifiable projected replay | Accepted. `projection.source` carries `prev_hash` and `hash`; `verify_projection` returns the stub for chain and receipt checks. |
| R2-4 | Inconsistent choice consensus | Accepted. All deciders must consent to the same option; otherwise the tension is split, treated as a refusal (replan). `tally_choice`. |
| R2-5 | Replan retains an active commitment | Accepted. Replan supersedes the active commitment and closes consent requests in the same transaction; replacement needs a new commitment and fresh approval. |
| R2-6 | Join rejected before registration | Accepted. `join` is exempt from `unknown_participant`; checked against invitation and connection. No rejoin after leave. |
| R2-7 | Pending-withdrawal stage rejection | Accepted. `decided` accepts `commit(withdrawn)` for a pending commitment; the task returns to `negotiating`. |
| R2-8 | Unbound match-to-task | Accepted, with a smaller binding than suggested: `task_id` in every match payload plus a host exchange record; the PSI context digest and vector blobs stay unchanged because the envelope signature already covers the payload. |
| R2-9 | Commitment-ID allocation | Accepted. Members mint the ULID; the host rejects reuse. |
| R2-10 | Decision expiry | Accepted. `decision_deadline` on `propose` and `tension`; late decisions get `deadline_exceeded`; expiry is evaluated lazily from the log and the clock. Commitment, task and charter subjects have no own deadline. |

### Host ambiguities resolved (from the host builder's notes)

- **H1. How planning starts.** No new message: the first host `query` (with `task_id`), `propose` or `tension` naming an open task moves it to `negotiating`.
- **H2. Binding match and tension to tasks.** `match.task_id` and `tension.task_ids` are explicit; the host no longer infers them from `causation_id`.
- **H3. Plan sets.** Deciding one plan supersedes the other plans of its proposal set.

## Still open or accepted with a deferral

- **N1. Owner identity binding (open).** `owner_proof` proves possession of the owner key and binds it to the participant, but nothing yet proves that the key belongs to the named person or organization. v0.1 relies on the invitation and the organizer's admission. A verifiable credential or an identity-provider assertion could be added in a minor version.
- **N2. PSI count mode (accepted, deferred to v0.2).** v0.1 PSI is secure against semi-honest participants only. A malicious requester could blind each element with a different scalar in `count` mode and learn which elements matched. v0.1 therefore allows `count` only from a requester named in the charter's `count_trusted`, and `overlap` is the default. A zero-knowledge proof that one scalar blinds all request points is deferred to v0.2.
- **N3. PSI blob framing (resolved).** The spec's PSI section now describes the vault implementation byte for byte (signed `CKP1` headers, 16-bit counts and length prefixes, ECDH-encrypted request and response lists), because the encrypted channel stops the relaying host comparing tokens; `spec/vectors/psi.json` follows the implementation.
- **N4. Host key rotation (open).** Members pin the host key from the invitation. Rotation and revocation of the host key, and how old receipts stay verifiable afterwards, are not specified.
- **N5. Replay stubs (open).** Log replays substitute `{seq, prev_hash, hash}` for events outside the reader's scope so the chain still verifies. A stub reveals that an event exists and when; whether that is acceptable for `self` and `host` scoped events needs a privacy review.
- **N6. Charter refusal (open).** A member that refuses a charter revision keeps its offers and commitments uncounted. Whether the host must then remove it, and who may waive acceptance, is not defined.
- **N7. `task` subject (open).** The `task` kind is allowed in `proposed` and `decided` for an assignee's owner to accept or decline an assignment. Its relation to commitment approval may be redundant; v0.1 keeps both.
- **N8. Case and Unicode of IDs (open).** Participant, offer and query IDs are compared as exact strings; no normalisation is specified.

## Known validator differences

- **Integer-valued floats.** JSON Schema 2020-12 accepts `200.0` as an integer; the strict models reject a float where an integer is declared. JCS makes both sign and hash identically, so only the validation answer differs.
- **Trailing newline in patterns.** Python's `re` lets `$` match before a final newline, so `jsonschema` accepts an ID like `<ULID>\n`; ECMA 262 (and the models) reject it. Use `ids.is_ulid` for strict checks.
- **Dependency note.** `import-linter` has no partial wildcard, so the "contracts imports no other coalitionkit package" contract lists the planned package names; add new ones to `pyproject.toml`.
