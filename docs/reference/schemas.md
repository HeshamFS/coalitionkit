# Schemas

<!-- Written by tools/gen_docs.py. Edit the source, then run it again. -->

Every message is checked against a JSON Schema (2020-12). A pack adds fields only inside `ext`, and never changes these. A message that fails is refused as `schema_invalid`.

| File | Id | What it describes |
|---|---|---|
| [`answer.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/answer.json) | `https://coalitionkit.dev/schemas/coalition/v0/answer.json` | Vault to host: yes, no or a cost. The only thing a vault returns. |
| [`charter.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/charter.json) | `https://coalitionkit.dev/schemas/coalition/v0/charter.json` | Host to members: the Coalition's goal, roles, rules and deadline. |
| [`commit.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/commit.json) | `https://coalitionkit.dev/schemas/coalition/v0/commit.json` | Member to host: create (pending) or withdraw a commitment to a task. Approval is never sent here: it comes from an owner-signed coalition.decide. |
| [`common.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/common.json) | `https://coalitionkit.dev/schemas/coalition/v0/common.json` |  |
| [`decide.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/decide.json) | `https://coalitionkit.dev/schemas/coalition/v0/decide.json` | Member to host: one decider's answer on one revision of a plan, tension option, commitment, charter or task, signed by the decider's OWNER key in consent_sig. |
| [`dissolve.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/dissolve.json) | `https://coalitionkit.dev/schemas/coalition/v0/dissolve.json` | Host to members: the final message of a Coalition. |
| [`done.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/done.json) | `https://coalitionkit.dev/schemas/coalition/v0/done.json` | Member to host: a task is done, with evidence. |
| [`envelope.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/envelope.json) | `https://coalitionkit.dev/schemas/coalition/v0/envelope.json` |  |
| [`error.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/error.json) | `https://coalitionkit.dev/schemas/coalition/v0/error.json` | Host to sender: why an envelope was rejected. Scoped to its sender. |
| [`join.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/join.json) | `https://coalitionkit.dev/schemas/coalition/v0/join.json` | Member to host: asks to join with the listed roles and binds the owner's Ed25519 key to the participant. |
| [`leave.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/leave.json) | `https://coalitionkit.dev/schemas/coalition/v0/leave.json` | Member to host: withdraws the member. A reason is optional. |
| [`match.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/match.json) | `https://coalitionkit.dev/schemas/coalition/v0/match.json` | Vault to vault, relayed by the host: an opaque PSI blob about one task. |
| [`need.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/need.json) | `https://coalitionkit.dev/schemas/coalition/v0/need.json` | Host to members: something the Coalition needs. |
| [`observe.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/observe.json) | `https://coalitionkit.dev/schemas/coalition/v0/observe.json` | Edge to host: an observation with its source. |
| [`offer.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/offer.json) | `https://coalitionkit.dev/schemas/coalition/v0/offer.json` | Member to host: what the member can give toward a need or task. No free text. |
| [`projection.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/projection.json) | `https://coalitionkit.dev/schemas/coalition/v0/projection.json` | Host to member: a redacted or viewer-specific delivery of a logged event, signed by the host key. Never carries the sender's JWS. |
| [`propose.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/propose.json) | `https://coalitionkit.dev/schemas/coalition/v0/propose.json` | Host to members: plan universes, each member sees only its own assignments. |
| [`query.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/query.json) | `https://coalitionkit.dev/schemas/coalition/v0/query.json` | Host to vault: a typed question. |
| [`receipt.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/receipt.json) | `https://coalitionkit.dev/schemas/coalition/v0/receipt.json` | Host to sender, with every acknowledgement: the host-signed head of the log after the event. |
| [`ripple.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/ripple.json) | `https://coalitionkit.dev/schemas/coalition/v0/ripple.json` | Any participant: a change and the tasks it invalidates. |
| [`scope.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/scope.json) | `https://coalitionkit.dev/schemas/coalition/v0/scope.json` | Who may see an envelope. There is no default. |
| [`tension.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/tension.json) | `https://coalitionkit.dev/schemas/coalition/v0/tension.json` | Host to deciders: a conflict and its trade-offs. |
