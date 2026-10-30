# G1 runtime verification

## Implemented

- The runtime supplies membership and resolved recipients inside its write transaction. The
  server forwards these facts to the Steward without reading the host's private cache or
  opening a nested transaction.
- Consent to contact is membership: a participant consents by joining under the charter, so
  `consented` is the member set. `scope_check` already refuses a `participants` entry that is
  not a member, so the Steward's `no-contact-before-consent` policy cannot fire through the
  host today; it stays as defence in depth. Before this change `consented` was empty and the
  policy blocked every participants-scoped observe, offer and ripple. A separate contact
  consent (a member who may be addressed only after opting in) would need its own ledger.
- Feed connections retain an incremental projection and generate event-level RFC 6902
  additions. Membership changes rebuild the projection, including removals. Bus callbacks
  wake streams immediately; reads and folds run in worker threads. The timer remains for
  session housekeeping, not change detection.
- Postgres uses a bounded pool with checkout probes and capped reconnect backoff. An
  interrupted transaction is never automatically replayed. A2A reports HTTP 503 with
  Retry-After; the sender retries the original event ID and bytes. Health returns 503 and
  store=down during an outage. The driver import is deferred until a connection is needed.
- Steward construction and its self-test run in the background. While pending, proposals
  and policy findings are refused; other messages can be accepted. Initialization failure
  fails closed. Shutdown joins the initialization executor.

## Measurements

Command: `uv run python packages/acceptance/tests/measure_runtime_feed.py`.
This is a sequential, in-process SQLite comparison with 200 members, 10 viewers and
20 observations per mode. It compares the old full-fold feed path to the incremental path
in the same process. It does **not** measure HTTP concurrency, SSE transport or the
real-server acceptance targets.

| p95, seconds | Full fold | Incremental |
| --- | ---: | ---: |
| Send | 0.004582 | 0.004254 |
| Update all ten viewer feeds | 2.218498 | 0.012028 |

An initial fresh-process server import measured 2.9595 seconds; after these changes it
measured 3.2240 seconds. There is no demonstrated startup improvement. Policy loading
measured 0.00594 seconds and the self-test 0.00052 seconds. A separate import-time profile
attributed about 1.06 seconds cumulatively to models (0.99 to the OpenAI client) and
0.77 seconds to MCP. These are overlapping cumulative timings, not additive totals.
Further startup import work and end-to-end first-accept measurements remain outstanding.

## Verification and limits

Regression tests cover transaction context, consented versus non-member recipients,
incremental delivery, removal after leaving, wakeup before a 60-second timer, dead
connection replacement, backoff, no internal transaction replay, health recovery,
startup gating, and an HTTP 503 followed by two identical retries producing one append.
The final `tools/check.py` run exited 0: 1,112 tests passed, 23 skipped (not run),
with lint, formatting, type checks, import boundaries, schemas and the core rule passing.

Use a writable cache and temporary directory here:

```powershell
$env:UV_CACHE_DIR = "$PWD/.uv-cache"
$env:PYTEST_ADDOPTS = '-p no:cacheprovider --basetemp=.venv/test-tmp'
$env:COALITIONKIT_LIVE = '0'
& C:\Users\hisha\.local\bin\uv.exe run python tools/check.py
```

`uv sync` succeeds with that cache override. The default global cache is not writable.
The initial full check reached pytest but encountered 123 temporary-directory errors;
the workspace-local temporary directory resolves those errors.

The checkout does not contain `scale_server`, `chaos_server`, `test_scale_server.py` or
`test_chaos_server.py`. The requested acceptance command therefore ran no tests. Docker's
client is installed, but access to the desktop-linux engine pipe is denied. Real-server
before/after scale measurements and Postgres restart/drop chaos measurements (including
zero lost and zero duplicated events) remain unverified. Mocked connection failures are
not a substitute for those measurements. Live model tests were not run.
