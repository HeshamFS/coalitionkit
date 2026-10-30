# CoalitionKit conformance probes

Black-box protocol v0.1 probes. The runner imports contracts and client edges,
never server or runtime packages. Reports distinguish `pass`, `fail`, and
`not run`; incomplete coverage never produces exit 0.

    uv run coalitionkit-conform --target CARD_URL --level host --operator reference --admin-token-file TOKEN_FILE

The reference adapter creates an isolated Coalition with two deciders and
redeems invitations into externally signed members. The UTF-8 token file
contains only the admin bearer token. It is sent only to admin endpoints on the
target card's origin and is never included in reports. `--operator` and
`--admin-token-file` must be supplied together.

For operator-issued invitations:

    uv run coalitionkit-conform --target CARD_URL --level host --invite CODE1 --invite CODE2 --redeem-url REDEMPTION_URL

`--invite` repeats; `--invites-file` adds one code per UTF-8 line. Invitations
must identify distinct participants in one isolated Coalition. Without setup,
the runner tests discovery and reports the missing prerequisites.

## Reference operator contract

Other implementations provide their own `Operator` adapter, passed as
`run(..., operator=adapter)`. The adapter provisions fixtures; assertions use
signed protocol deliveries and authenticated member feeds.

- `create(charter)` uses `POST /admin/coalitions` and returns `coalition_id`,
  `host_card_url`, and `invitations` (`participant`, `invitation`).
- `invite(coalition, participant)` uses
  `POST /admin/coalitions/{coalition}/invitations`.
- `emit(coalition, kind, payload, scope=None, sources=None)` uses
  `POST /admin/coalitions/{coalition}/host-events`.
- `redeem_url` accepts `{invitation, card_url, card}` and returns
  `{coalition_id, participant, token}`.
- `feed_url` is an authenticated SSE endpoint with a `STATE_SNAPSHOT` frame.

All admin operations require the same `Authorization: Bearer TOKEN` credential.
The host-events request is `{type, payload, scope?, sources?}`; `sources` is an
optional list of source event IDs for scope derivation. The route calls
`CoalitionHost.host_emit` with these arguments, with normal validation,
authorization, revision assignment, scope enforcement and Steward review.
There are no policy overrides or clock controls.

Success is `{accepted, receipt}`, with the original signed acknowledgement
fields. A refusal is the original signed `coalition.error` envelope, returned
with HTTP 200. Invalid request structure returns 422, unknown Coalition 404,
and absent or incorrect admin credentials 401. Omitted scope preserves the
host's default: derive from sources when supplied, otherwise `host`.

Proposals and tensions carry `decision_deadline` in their normal payloads.
The runner waits for short real deadlines; it does not change existing
subjects' deadlines or replace the server clock. Unsupported adapter operations
raise `OperatorUnavailable` and are reported as `not run`.

C-12 uses the reference Steward's `fairness-cap-exceeded` policy: a proposal
assigning two tasks to one of two participants must be refused and absent from
both feeds. Other adapters must provision an equivalent known policy fixture
before using that probe. Public proposals require a working model audit. With
no model credentials the reference server refuses proposal setup with
`steward_blocked`; the affected IDs retain that failure and event reference.
This is a setup limitation, not evidence of a lifecycle defect.

## Coverage and remaining gaps

With a scripted model behind the real Steward, integration tests exercise
C-01, C-02, C-09 through C-16, and C-20. C-10 covers independent task stages and
pending commitment withdrawal. C-15 covers stale and duplicate decisions,
owner-key rejection, concurrent consent, split options, refusal, real deadline
expiry, disconnected consent, and fresh approval after replanning. C-20 covers
host-only types, wrong owners/assignees/deciders, hidden targets, repeated
answers, PSI party/task binding, and commitment-ID reuse.

C-11 verifies a contiguous mixed original/projection sequence delivered in A2A
acknowledgements, including kept receipts, and checks observer visibility in the
feed. The feed removes envelope metadata; it is not used as signed replay.
C-09 checks a contiguous concurrent segment, not a genesis replay endpoint.
C-16 runs all 20 local scope vectors plus a live private-source derivation and
an explicit widening refusal. An installed wheel without the vectors reports
the missing fixture.

The host level is still incomplete:

- C-03 and C-04 require observable target-member output. The current adapter
  enrolls runner-owned signers and cannot certify another member's generation.
- C-05 checks schema-invalid submission rejection and returned envelopes, but
  cannot certify target-member output generation.
- C-21 verifies commitment suspension and renewed charter consent, but the
  feed exposes events, not whether offers count toward planning. That coverage
  remains `not run` with partial evidence.

Vault C-06–C-08 and surface C-17–C-19 are excluded from `--level host`.

JSON goes to stdout and a readable table to stderr. `--key` accepts an
unencrypted Ed25519 PKCS8 PEM report key; otherwise one is generated in memory.
Detached JWS covers all report fields except `signature`. Verify with
`coalitionkit_conformance.report.verify_report`. The embedded public key proves
integrity, not publisher identity; pin publisher keys separately.

Exit 0 means all selected IDs passed, 1 includes failures or not-run tests,
and 2 denotes CLI configuration errors. Evidence gives submitted IDs,
sequences, or rejection codes. No admin token is printed.

Tests use real TCP and preserve broken-target regressions. Scripted model
responses are installed only in tests, behind the real Steward; production
code has no test clock or policy bypass. Scripted calls are not live model runs.

    uv run pytest packages/conformance packages/server -q
    uv run python tools/check.py
