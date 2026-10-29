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
the result to `Minted.approve`. Approval cannot be supplied as a boolean tool
argument. Tool consent uses the same payload with the tool name and arguments
excluding `signature`. Consumed operation signatures cannot be replayed.

Before approval, MCP calls from outside the proof runner are refused. The runner's
ephemeral capability is delivered through stdin and works only during proof.
Pausing revokes serving; edits use `pipeline.remint` to create another artifact
which requires fresh approval. Delete stops the process and removes only the
known artifact files, refusing unexpected contents.

The local process binds only to 127.0.0.1, runs in the artifact directory and
inherits an environment allowlist without credentials, proxies or Python startup
hooks. The template import allowlist and import-linter contract prohibit network
and process dependencies. This is the local fixed-template isolation boundary;
it is not a general-purpose sandbox for arbitrary code. Agent Cards advertise a
custom MCP binding; they do not advertise an unimplemented A2A membership endpoint.

The MCP SDK can discard extra tool arguments before invoking a Python function.
Validate raw `tools/call` arguments in middleware before SDK dispatch; checking
only function arguments misses oversized and injected extra fields. The fixed
attack suite caught this behavior and now checks that those requests are rejected.

The trusted `reader.run_reader` runs outside the serving process and accepts a
capture callback returning fresh frames. It segments and re-reads them on the
configured interval, appends confident finite readings, and never sends a device
write. Missing updates make `status` stale. `catalog_data()` supplies data for the
existing Mint components, including schedule or device projections.

Run acceptance against two caller-provided videos and Windows-synthesized WAVs:

```powershell
python -m coalitionkit_mint.acceptance --resource-video <path> --resource-voice <path> `
  --device-video <path> --device-voice <path> --output <new-directory>
```

Set `COALITIONKIT_LIVE=1` and `COALITIONKIT_META_API_KEY` in the environment. The
runner writes gitignored `packages/mint/scorecard-*.json`, measuring elapsed time,
attacks, tokens and integer micro-USD from the shared meter. It stops measured
servers after recording results. Live tests generate neutral images with Pillow,
encode videos with ffmpeg and synthesize speech with Windows System.Speech; other
platforms skip speech synthesis explicitly. Scripted tests use generated PCM WAVs
and scripted transcription, segmentation and strict JSON replies.
