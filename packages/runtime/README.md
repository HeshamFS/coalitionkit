# Runtime library

`CoalitionHost` owns one coalition. Construct it with `SQLiteStore` (default in-memory,
optional file path) or `PostgresStore(url)`, the host card URL and signing key. Call
`create()` once, then `host_emit("charter", payload, scope)`.

Adapters verify cards, key expiry and revocation, then call `pin_card()` with the
verified key, key ID and authenticated participant/card binding. The organizer
must also call `invite(AuthenticatedSender(...))` before a first join. Reinstall
trusted pins and outstanding invitations after process restart. A participant
that left cannot rejoin; owner keys cannot be shared between participants. `accept(envelope, AuthenticatedSender(...))`
returns an `Acknowledgement` or a signed error envelope. Its `accepted` field is
the original, a host-signed projection, or `None` for receipt-only delivery;
`receipt` is always present. Duplicate acknowledgements obey the same rule. Transport activation is
represented by `extension_activated`; no transport code lives in this package.

`host_emit()` assigns revisions and can mint need, plan and tension IDs. Pass all
source event IDs through `sources`; omitted scopes are derived with the contracts
scope resolver. A `query` with `task_id`, `propose`, or `tension` starts planning
an open task. Match rounds carry `task_id`; tensions carry `task_ids`. Proposals
and tensions require `decision_deadline`. Expiry is applied from the log and
clock on writes and reads. Replans supersede active commitments and close their
consent requests; replacements need a new member-minted ID and fresh approval.

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
