# Notes from the acceptance runs

Problems found in other packages. Nothing here was changed; each entry gives the failing scenario.

1. Runtime: pinned cards and invitations are not in the store. After a host is rebuilt from the
   same store (`CoalitionHost(store, same_id, ...)`), every member's next message is refused
   with `bad_signature` until `pin_card` and `invite` are called again. Scenario:
   `chaos.kill_and_restart` has to re-attach each member by hand (`Arena.restarted`). The
   protocol's restart story needs the edge to re-verify cards on the first message, or the host
   to persist them.
2. Runtime: every `accept` rebuilds the whole State from the log and re-requests consents for
   every subject (`_snapshot`/`_transaction`), so one accept costs O(events). Measured at full
   size (200-agent Coalition, 802 accepts): p50 0.117 s, p95 0.164 s per accept, and one
   `view()` of the last agent took 1.26 s. Fine for the PR sizes; it will not hold for
   Coalitions with tens of thousands of events.
3. Edges and runtime: there is no `HostPort` adapter for `CoalitionHost`. The edge hands over a
   card URL string; the host wants an `AuthenticatedSender` (card URL plus participant), and the
   import-linter contracts stop edges from importing the runtime. `wire.CoalitionPort` is the
   only adapter and lives in this package.
4. Runtime, refusal code: once a decision settles a subject, a second answer from a decider is
   refused with `stage_mismatch` (task already decided), not `not_authorized`/`stale_subject`.
   Seen in `chaos.concurrent_deciders` (28 to 32 of 40 duplicate answers per run) and over A2A in
   `wire.run_wire`. The outcome is right (one decision per revision); the code may surprise
   clients that retry.
5. Not exercised: `PostgresStore`. `chaos.kill_and_restart` accepts `COALITIONKIT_TEST_DATABASE_URL`
   but no database was available here, so only SQLite runs were measured.
6. The cost fixture (`fixtures/usage.json`) is in the shape of a provider usage export with
   charges computed by exact decimal arithmetic; it is not a download from a provider. Point
   `COALITIONKIT_ACCEPTANCE_USAGE_FILE` at a real export in the same shape for the live check.
