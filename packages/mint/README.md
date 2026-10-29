# The Mint

`coalitionkit_mint.pipeline.mint` takes local video and WAV paths, a destination,
the owner's public key, a metered `ModelGateway` and a `MediaClient`. It returns a
running `Minted` handle only after all MCP attacks pass. Call `close()` in a
`finally` block to stop the child process.

Models return bounded JSON. The resource and device templates are reviewed Python
modules at version 1.0.0; artifacts contain JSON, SQLite, discovery metadata and
a SKILL.md. They contain no generated Python. Resource windows are minutes from
midnight in a single schedule; durations and occupancy limits are enforced inside
SQLite write transactions. Prerequisites require an owner signature over the
requested hold, and confirmation and cancellation always require owner signatures.

The manifest contains a unique artifact identity, template version, config hash
and owner public key. Sign `artifact.consent_payload(hash, "approve", {})` with
`coalitionkit_contracts.signing.sign_detached(..., owner_key, "owner")`, then pass
the result and owner key to `Minted.approve(signature, owner_key)`. Approval cannot be supplied as a boolean tool
argument. Tool consent uses the same payload with the tool name and arguments
excluding `signature` and the returned `state`. Holds have server-issued IDs, bounds,
a single-use nonce and a revision. Confirm and cancel bind all five fields; use
the updated revision returned by confirm when cancelling. Verified operation
proofs are consumed transactionally. Prerequisite attestations for hold creation
require a `hold_challenge` nonce bound to the exact request, expiring after 60 seconds.
Include that nonce in the signed `hold_slot` arguments. Every verified operation proof
is consumed even if policy refuses the operation; retry with a fresh challenge. The card is signed by the owner at approval
and includes a hash of the approval proof. Pending discovery is unsigned.

Before approval, MCP calls from outside the proof runner are refused. The runner's
ephemeral capability is delivered through stdin and works only during proof.
Pausing revokes serving; edits use `pipeline.remint` to create another artifact
which requires fresh approval. A failed re-mint leaves the old server serving;
a successful replacement pauses it. Delete stops the process and removes only the
known artifact files, refusing unexpected contents.

The local process binds only to 127.0.0.1, runs in the artifact directory and
inherits an environment allowlist without credentials, proxies or Python startup
hooks. The AST template import allowlist prohibits unreviewed imports, including network
and process dependencies. This is the local fixed-template isolation boundary;
it is not a general-purpose sandbox for arbitrary code. Agent Cards advertise a
custom MCP binding; they do not advertise an unimplemented A2A membership endpoint.

The MCP SDK can discard extra tool arguments before invoking a Python function.
Validate raw `tools/call` arguments in middleware before SDK dispatch; checking
only function arguments misses oversized and injected extra fields. The fixed
attack suite caught this behavior and now checks that those requests are rejected.

The trusted `reader.run_reader` runs outside the serving process and accepts a
capture callback returning fresh frames. It segments and re-reads them on the
configured interval, records conversion errors and appends confident finite readings, and never sends a device
write. Missing updates make `status` stale. `catalog_data()` supplies data for the
existing Mint components, including schedule or device projections.

Run acceptance against two caller-provided videos and Windows-synthesized WAVs:

```powershell
python -m coalitionkit_mint.acceptance --resource-video <path> --resource-voice <path> `
  --device-video <path> --device-voice <path> --output <new-directory>
```

Set `COALITIONKIT_LIVE=1` and `COALITIONKIT_META_API_KEY` in the environment. The
runner writes `scorecard-*.json` under the selected output directory, measuring elapsed time,
attacks, tokens and integer micro-USD from the shared meter. It stops measured
servers after recording results. Live tests generate neutral images with Pillow,
encode videos with ffmpeg and synthesize speech with Windows System.Speech; other
platforms skip speech synthesis explicitly. Scripted tests use generated PCM WAVs
and scripted transcription, segmentation and strict JSON replies.

Perception tries short template-specific phrases in order and falls back to the
whole frame. Scorecards include each selected phrase or `whole_frame`.

The proof suite uses an isolated artifact with the exact configuration and a test
owner, exercises real MCP calls with valid prerequisite signatures, and checks
explicit refusal codes alongside successful controls. Window and overlap
mutation tests ensure removing either check fails the suite.
