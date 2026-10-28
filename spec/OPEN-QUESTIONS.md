# Open questions and schema choices (Coalition Protocol v0.1)

Where the spec leaves a field's inner shape open, the schemas use the smallest shape that works.
Each choice is listed here so the spec text can adopt it or replace it. Every choice below is
mirrored in `spec/schemas/coalition/v0/*.json` and in `packages/contracts`.

## Choices made

| # | Area | Choice | Why |
|---|---|---|---|
| 1 | Signature form | `sig` is a compact JWS with a **detached payload**: `<protected>..<signature>`. The verifier rebuilds the payload (JCS of the envelope without `sig`, `seq`, `ts`, `prev_hash`). Protected header is exactly `alg: EdDSA`, `typ: JOSE`, `kid`, written in JCS form. | The spec says "compact JWS over the JCS-canonical envelope" and does not say attached or detached. Detached avoids carrying the envelope twice and a payload that can disagree with the envelope. |
| 2 | Integer range | Every integer is limited to 0..2^53-1 in the schemas and models (`seq` and `revision` from 1). | `rfc8785` refuses larger integers, so a larger value could never be signed or hashed. Money (minor units) is bounded by this too. |
| 3 | `coalition.error` | `error.json` is the payload schema for type `coalition.error`: `code` (the 14 codes), `detail` (object), `ref` (a ULID, the `event_id` answered). `coalition.error` is a payload type but not one of the sixteen. | The spec lists errors as a message with `code`, `detail`, `ref`. |
| 4 | Error `detail` | Object, all keys optional: `message` (string), `policy_id` (string), `retry_after_ms` (integer). | The spec uses `detail` both as free explanation, as the policy ID (`steward_blocked`) and as `detail.retry_after_ms` (`rate_limited`). |
| 5 | Scope | Only `audience` is required. `participants`, `roles`, `redact` optional. `audience: participants` needs a non-empty `participants`; `audience: roles` needs a non-empty `roles`. `redact` entries start with `payload.`. Lists have unique items. | "No default scope" is in the spec; the cross-field rules follow from the audience table. |
| 6 | Common types | `id` = string, 1 to 128 characters (participant, task, need, offer, query, plan IDs and the like). Only `coalition_id`, `event_id`, `causation_id`, `correlation_id` and `error.ref` are ULIDs. | The spec requires ULIDs for the envelope IDs only. |
| 7 | `charter` | `roles`: non-empty list of `{id, required?}`; `rules`: list of non-empty strings; `deadline`: RFC 3339 date-time; `pack`: `{name, version}`; `budget`: `{amount (minor units), currency (ISO 4217, three capitals)}`. Added optional `deciders` (list of participant IDs) and optional `version` (integer >= 1). | Spec: "updated charters carry a new version" and "participants named as deciders in the charter". Neither field was listed; with `additionalProperties: false` they must exist to be usable. |
| 8 | `join` | `card_url`: URI; `owner_proof`: non-empty string (opaque); `roles_requested`, `surfaces`: unique lists of IDs; `vault`: `local` or `hosted`. | Spec leaves proof and surface vocabulary open. |
| 9 | `leave` | No required field; optional `reason` (string). | Spec: "a reason is optional and never required". |
| 10 | `observe` | `content` is a string (may be empty); `evidence_ref` is an ID. | Smallest shape; structured content belongs in discipline packs. |
| 11 | `need` | `requirements`: list of non-empty strings; `window`: `{start, end}` date-times. | Spec lists the names only. |
| 12 | `offer` | `target`: `{kind: need or task, id}`; `capacity`: integer >= 1; `cost`: `{minutes, money (minor units), effort: low, medium or high}`, all three required; `valid_until`: date-time. No currency in a cost: it is the Coalition's budget currency. | Spec: "`cost` has `minutes`, `money` and `effort`; no free text". |
| 13 | `query` | `subject` is an ID; `deadline_ms` integer >= 1 and **required** (see ambiguity A4). | |
| 14 | `answer` | `result` is exactly one of: `"yes"`, `"no"`, or a `cost` object (same shape as in `offer`). | Spec: "`yes`, `no` or a cost". |
| 15 | `match` | `blob` is a base64url string (no padding). | Spec says opaque blob; base64url keeps it JSON-safe. |
| 16 | `propose` | `plans`: non-empty list of `{plan_id, revision, assignments: [{task_id, assignee}], objective_scores: {name: number}}`. `objective_scores` is an open map by design. | The `revision` is needed so a `decide` can name it (A5). |
| 17 | `tension` | `options`: at least two `{option_id, summary}`; `tradeoffs`: list of strings; `deciders`: non-empty unique IDs; optional `revision`. | |
| 18 | `decide` | `subject`: `{kind: plan, tension_option or commitment; id; revision >= 1}`; `choice`: an ID; `consent`: boolean. The revision is required. | Spec rule 5: a decision names the revision it answers. |
| 19 | `commit` | `status`: `pending`, `approved`, `withdrawn`; optional `revision`. | See A6. |
| 20 | `ripple` | `change`: non-empty string; `invalidates`: unique list of task IDs. | |
| 21 | `done` | `evidence`: list of `{kind, ref, verified_by}`, all required non-empty strings. | |
| 22 | `dissolve` | `skills_written`: list of IDs. | Spec leaves its type open. |
| 23 | Formats | `date-time` and `uri` are asserted by the validator (format checker enabled). The Pydantic models check the same with an RFC 3339 pattern and "absolute URI with a host". Date-times stay strings in the models so the signed bytes never change on re-serialisation. | |
| 24 | Strictness | Models are strict: no coercion (`"1"` is not an int, `true` is not an int) and an explicit `null` is invalid, matching the schemas, which have no nullable field. | |
| 25 | Shared definitions | A `common.json` schema holds shared `$defs` (`id`, `cost`, `window`, `target`, `budget`, `datetime`, `revision`, `money`, `ulid`). | Avoids repeating shapes across payload schemas. |

## Ambiguities and contradictions found in the spec text

- **A1. Placeholder domain.** The spec shows `$id: https://<project-domain>/schemas/...` and says the domain becomes `coalitionkit.dev` once registered. The schemas already use `https://coalitionkit.dev/schemas/coalition/v0/`, as asked.
- **A2. Charter deciders.** Rule 4 says deciders are "named in the charter or the tension", but the charter's field list has no deciders field. Added as optional (choice 7).
- **A3. `approve_commitment` and revisions.** The MCP tool `approve_commitment` takes only `commitment_id`, yet it becomes a `coalition.decide` whose subject needs a revision (rule 5). The MCP server has to fill in the current revision; the spec should say so.
- **A4. `deadline_ms`.** The table lists `deadline_ms` as required, the Timeouts paragraph says "default 10,000". Both cannot hold for a required field. Schema: required. If a default is intended, the field should move to optional.
- **A5. Where a revision comes from.** Rule 5 requires a decision to name a revision, but no message says who assigns it. Chosen: `propose` plans carry `revision` (required), `tension` and `commit` carry an optional `revision` (a missing one counts as 1). The host must define how a revision increases.
- **A6. `commit` status `approved`.** The type table lets a member send `commit` with status `approved`, yet also says "approved only by a `coalition.decide` from the owner". Whether a member's `commit` may carry `approved` is not defined; the schema allows the enum value and leaves the check to the host (stage and role rules).
- **A7. Error `ref` when there is no event ID.** `coalition.error` must carry the `ref` of the event answered, but a `schema_invalid` envelope may have no valid `event_id`. The schema requires a ULID `ref`; the host needs a rule for this case (for example the host's own new ULID).
- **A8. Stage table versus task rule.** The stage table says Act accepts `commit`, `decide`, `done`, `ripple`, while the text says `answer`, `match`, `offer` about a negotiating task are accepted in any stage from Negotiate to Live. Both are consistent only if the text overrides the table; stated here so the stage tests cover it.
- **A9. Dissolve stage.** Dissolve accepts only `leave` from members, but `done` for tasks finishing at the deadline is not accepted there. Probably intended.
- **A10. `type` pattern versus sixteen types.** The envelope pattern `^coalition\.[a-z_]+$` accepts any name; only the sixteen types plus `coalition.error` have payload schemas. An unknown type fails in `validate_envelope`, not in `envelope.json`.

## Known validator differences

- **Integer-valued floats.** JSON Schema 2020-12 accepts `200.0` as an integer; the strict models reject a float where an integer is declared. JCS makes both sign and hash identically, so only the validation answer differs.
- **Trailing newline in patterns.** Python's `re` lets `$` match before a final newline, so `jsonschema` accepts an ID like `<ULID>\n`; ECMA 262 (and the models) reject it. Use `ids.is_ulid` for strict checks.
- **Dependency note.** `import-linter` has no partial wildcard, so the "contracts imports no other coalitionkit package" contract lists the planned package names; add new ones to `pyproject.toml`.
