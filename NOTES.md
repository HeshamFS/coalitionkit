# Vault / PSI handoff

- Added `packages/vault`, deterministic vectors, workspace dependency, strict
  pyright inclusion, and import boundaries. No commits or git configuration changes.
- PyNaCl 1.6.2 installs on Python 3.15.2 but exposes no ristretto255 operations.
  PySodium 0.7.19 installs and executes libsodium ristretto255 operations here.
  It discovers libsodium 1.0.20 at `C:\tools\php84\libsodium.dll`; deployment must provision a trusted
  libsodium installation. The Python binding and new protocol have no claimed
  independent audit. All group arithmetic is in libsodium.
- Byte layout and threat model: see `packages/vault/README.md`. Signed `CKP1`
  headers bind the context and round; lists have big-endian 16-bit counts and
  16-bit length prefixes for 32-byte points. Request/response lists use a separate
  ephemeral ECDH encrypted channel so the relay cannot compare matching tokens.
- Count responses independently shuffle doubled requester tokens to hide label
  associations. This is an honest-participant PSI construction, not a protocol
  with proofs against malicious endpoints. The relay learns set sizes.
- Root `NOTES.md` is included because the slice explicitly requested it, although
  the earlier scope list did not enumerate it. The pyright include list was also
  extended as required by the done criteria.
- Out of scope: provisioning libsodium, transport deadline enforcement, signing-key
  discovery/pinning, and authorization/rate limits for repeated PSI queries.
- Validation: `uv sync` succeeded using workspace-local `UV_CACHE_DIR=.uv-cache`
  (the default cache is not writable here). `uv run python tools/check.py` passed:
  284 tests, strict pyright including vault, ruff, import boundaries, schemas and
  the agnostic-core rule. `git diff --check` also passed. Vectors reproduce in tests.
