# Runtime library

`CoalitionHost` owns one coalition. Construct it with `SQLiteStore` (default in-memory,
optional file path) or `PostgresStore(url)`, the host card URL and signing key. Call
`create()` once, then `host_emit("charter", payload, scope)`.

Adapters verify cards, key expiry and revocation, then call `pin_card()` with the
verified key, key ID and authenticated participant/card binding. Reinstall these
trusted pins after process restart. `accept(envelope, AuthenticatedSender(...))`
returns an `Acknowledgement` or a signed error envelope. Transport activation is
represented by `extension_activated`; no transport code lives in this package.

`host_emit()` assigns revisions and can mint need, plan and tension IDs. Pass all
source event IDs through `sources`; omitted scopes are derived with the contracts
scope resolver. A `query` starts planning an open task. Match setup and tensions
use `causation_id` to bind their otherwise unspecified task references.

`state_document()` is the host's complete JSON state. `view(participant)` folds
visible deliveries into an event-indexed JSON document; `patch(old, new)` produces
an atomic RFC 6902 replacement when it changes. `replay()` returns originals,
host-signed projections, or chain stubs. Only trusted internal callers use the
`host` and `steward` viewer identities. Adapters bind all other reads to the
request's authenticated participant. The bus contains wakeups only; its raw-log
reader is an internal port, not a viewer delivery API.

The event row stores original signed bytes as JSON plus host fields and the
Steward's delivery redaction paths. Paths are committed atomically with the event
and cannot be updated or deleted through the store. They also constrain derived
outputs. A Steward block, quarantine, or escalation holds the submission before
append and returns `steward_blocked`; no automatic human escalation transport is
provided. The hook runs on all submissions, including every proposal.

SQLite uses `BEGIN IMMEDIATE`; PostgreSQL locks the coalition counter row. The
counter, event, durable consent changes and receipt commit together. A failed
transaction rolls them all back. State is rebuilt from accepted events; owner
keys, decisions, revisions, task statuses and charter acceptance survive restart.
PostgreSQL conformance checks require `COALITIONKIT_TEST_DATABASE_URL` and use
unique coalition IDs without deleting persisted audit history.
