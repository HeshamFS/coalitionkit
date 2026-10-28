# coalitionkit-vault

Private typed records and three-round ECDH private set intersection. Group
operations use PySodium 0.7.19 and the audited libsodium implementation of
ristretto255. PyNaCl 1.6.2 installs on CPython 3.15.2 but exposes no ristretto255
operations. PySodium installs and its group operations execute on that runtime.
PySodium itself is a binding; no independent audit of this Python binding or this
exchange is claimed. A system libsodium with ristretto255 support must be installed
and discoverable by PySodium. No Python group arithmetic is implemented here.

## Typed answers

Register `Facts` by public subject ID with `Vault.put`. Free slots are validated,
positive-duration RFC 3339 intervals; capacities are nonnegative integers with
units; sets contain private strings. `feasible` is yes if any slot, positive
capacity, or nonempty set exists. `availability` means a free slot exists. `cost`
returns the explicitly registered tariff for a feasible subject, otherwise no.
Unknown subjects always return no. Query subjects are opaque identifiers, so no
quantity, time window, or textual instructions are inferred from them.

`deadline_ms` is a response budget, not a date or availability window. The caller
supplies elapsed time since receipt; an expired budget raises `DeadlineExceeded`
instead of emitting a late answer. The transport must also enforce delivery time.
Private notes are stored separately and never read by the answer calculation.
`Canaries.plant` and `Canaries.scan` support extraction testing, including escaped
JSON text. Scanning does not claim to detect arbitrary encodings or transformations.

## Exchange and byte layout (version 1)

Pin each participant's Ed25519 public key through the authenticated identity layer
before constructing `Requester` or `Responder`. Do not trust keys supplied by the
relay. Create fresh objects for every match. Production must omit every `test_*`
argument. The deterministic vector uses explicitly marked TEST ONLY seeds,
scalars and input ordering; count mode reverses requester tokens in that fixture.

The responder sends `setup`; the requester sends `request`; the responder sends
`response`. Only `Requester.finish` exposes the result. All blobs use unpadded,
canonical base64url. The decoded layout is:

| Field | Bytes |
|---|---:|
| ASCII `CKP1` | 4 |
| Round (`setup=0`, `request=1`, `response=2`) | 1 |
| Context digest C | 32 |
| Round body | variable |
| Ed25519 signature over all preceding bytes | 64 |

C is SHA-256 of JCS of `["coalition-psi-v1", coalition_id, match_id,
requester_id, responder_id, reveal]`. The participant pair is ordered by role.
Every element is mapped from `C || JCS(element)` using RFC 9380 SHA-512 XMD,
64 output bytes and libsodium's ristretto255 map. The DST is the ASCII string
`CoalitionKit-v0.1-PSI-ristretto255_XMD:SHA-512_R255MAP_RO_`.

Each point list is an unsigned 16-bit big-endian count, then count repetitions
of unsigned 16-bit big-endian length (always 32) followed by a 32-byte canonical
ristretto255 point. Identity, invalid points, duplicates, trailing bytes, more
than 1,024 points, and encoded blobs longer than 94,000 characters are refused.
Inputs are exact Unicode strings, without normalization, at most 4,096 UTF-8
bytes each. Duplicate inputs are refused before shuffling.

Each party generates independent random channel and PSI scalars. Setup body is
the responder's 32-byte channel public point. Request body is the requester's
32-byte channel public point followed by encrypted requester PSI points. Response
body is encrypted doubled requester points followed by responder PSI points.
Lists initially follow independently random permutations of each party's inputs.
Overlap response preserves the already shuffled requester order for local label
recovery. Count response independently shuffles that list again, breaking label
association; the requester computes only the size of the token intersection.

Channel shared secret S is ristretto255 ECDH. Request key is SHA-256 of
`"coalition-psi-channel-v1" || C || S`; response key is SHA-256 of
`"response" || request_key`. Encryption is ChaCha20-Poly1305, including its 16-byte
tag. Each directional key encrypts exactly one message, with twelve zero nonce
bytes. AAD is `C || ASCII(round) || SHA256(transcript)`. Request transcript is
the ASCII setup blob; response transcript is the ASCII setup blob concatenated
with the ASCII request blob. Signatures bind every body to its context and round;
AEAD binds responses to the complete prior transcript. Replay and wrong-order
calls fail state checks. New exchanges must use fresh scalars, even if IDs repeat.

## Security boundary

The relay sees identities, rounds, and set cardinalities through lengths. It sees
no comparison tokens, matching positions, plaintext elements, or overlap count.
Signatures reject relay alterations; encryption prevents token equality tests.
The tests exercise dictionary guesses (including actual inputs), equal-length
transcripts with different overlaps, cross-context substitution and tampering.
These regression checks are not a proof of computational indistinguishability.

The PSI construction assumes parties execute their scalar multiplication and
shuffle honestly. It does not include proofs of correct evaluation or protection
against malicious endpoint implementations. Repeated chosen-set queries can
reveal private data; authorization and query budgets belong to the caller.
Count-only disclosure includes facts logically implied by the count and known
input sizes. Nothing here claims process-memory isolation or secure Python
secret erasure. The host must never receive vault objects or endpoint secrets.
