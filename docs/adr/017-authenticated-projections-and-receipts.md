# ADR 017: Authenticated projections and receipts

Status: Accepted

## Decision

The log keeps every original signed envelope. Anything the host delivers with a field redacted, or projected for one viewer, is a `coalition.projection`: an envelope signed by the host key that names its source (`event_id`, `seq`, `type`, `on_behalf_of`, and the original entry's `prev_hash` and `hash`, which let a replay check the chain through the projection) and carries the projected payload. It never carries the sender's JWS and is never appended to the log. Recipients verify projections against the host key they pinned. Originals are delivered only when no field is redacted for that recipient.

Every acknowledgement also carries a host-signed `coalition.receipt` `{coalition_id, seq, head_hash}`. The `prev_hash` of seq 1 is the SHA-256 of the JCS form of `{coalition_id, host_card_url, created_at}`. A member that keeps its receipts can detect an edited or truncated tail.

R2: an acknowledgement follows the same delivery rule: the original, a projection, or only the receipt for a sender outside the scope.

## Why

A redacted copy of an envelope cannot verify against the sender's signature, and forwarding the original signature next to altered content invites a recipient to trust fields that were never signed in that form. A host signature on exactly what was delivered makes the trust boundary explicit. The hash chain alone cannot see an edited last entry or a cut tail, because nothing follows it; receipts give each member a host commitment to the log head that the host cannot later contradict.

## Rejected alternatives

- Delivering redacted copies under the sender's original signature (the signature fails, or the recipient is told to ignore it).
- Per-field signatures or Merkle redaction (heavier, and every sender would need it).
- A single published log head without per-event receipts (a member could not prove what it was told).
