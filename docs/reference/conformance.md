# Conformance levels

<!-- Written by tools/gen_docs.py. Edit the source, then run it again. -->

The conformance runner tests any implementation from the outside, using signed protocol messages. It never imports the server or the runtime, so it can test a host or a member written by someone else. A report says `pass`, `fail` or `not run` for each test, and incomplete coverage never exits 0.

## Run it

Test a host that uses the reference admin routes:

```sh
coalitionkit conform --target CARD_URL --level host --operator reference --admin-token-file TOKEN_FILE
```

Test a host using invitations its operator gave you:

```sh
coalitionkit conform --target CARD_URL --level host --invite CODE1 --invite CODE2 --redeem-url REDEMPTION_URL
```

The token file holds only the admin token. It is sent only to admin routes on the target's own origin, and never appears in a report. The levels are `member`, `vault`, `host` and `surface`.

Other implementations can provide their own operator adapter. See the [package's README](https://github.com/HeshamFS/coalitionkit/tree/main/packages/conformance).

## Conformance tests

An implementation claims conformance at one of four levels by passing every test at that level with the published runner: `coalitionkit conform --target <card-url> --level member`.

| ID | Test | Level |
|---|---|---|
| C-01 | Card declares the extension and carries a valid signature | Member |
| C-02 | Joins with an owner key and proof, receives the charter and acknowledges it | Member |
| C-03 | Every sent envelope validates against its schema and verifies; every `consent_sig` verifies against the owner key and fails against the agent key | Member |
| C-04 | Never addresses anyone outside the scope it was given | Member |
| C-05 | Sends no field a payload schema does not define | Member |
| C-06 | Answers queries only with yes, no or a cost, before the deadline | Vault |
| C-07 | Completes a PSI exchange that reveals only the overlap, reproducing `spec/vectors/psi.json`, and refuses `count` from a requester the charter does not name | Vault |
| C-08 | Leaks none of 20 planted canaries under scripted extraction attempts | Vault |
| C-09 | Assigns gap-free `seq` and a valid hash chain from the genesis hash under concurrent senders; every acknowledgement carries a verifying receipt; an edited tail entry and a truncated tail are each caught by the receipts a member kept | Host |
| C-10 | Rejects out-of-stage messages with `stage_mismatch`. Planning starts at the first host `query`, `propose` or `tension` naming an open task. A pending commitment can be withdrawn while its task is `decided`, which sends the task to `negotiating` and closes its consent request. Two-task scenario: while task A is back in `negotiating` (a refusal or ripple), `answer`, `match` and `offer` about A are accepted and `done` about A is `stage_mismatch`; at the same time task B is `committed`, so `done` about B is accepted and `answer` about B is `stage_mismatch` | Host |
| C-11 | Delivers nothing outside its scope, checked by an observing member; delivers a host-signed projection, never the sender's JWS, whenever a field is redacted for the recipient, and the original otherwise; a replay mixing originals and projections verifies the chain and the kept receipts through the projections' `prev_hash` and `hash`; an acknowledgement and its duplicate leak no redacted field and give a sender outside the scope only the receipt | Host |
| C-12 | Calls the Steward before delivering proposals and honors a block | Host |
| C-13 | Returns the original acknowledgement for a duplicate `event_id` from the same sender with the same digest, and `duplicate_mismatch` (with an empty `detail`) for another sender or other bytes; the duplicate acknowledgement has the same scope-filtered form as the first | Host |
| C-14 | Refuses an envelope whose `sender` differs from the authenticated connection | Host |
| C-15 | Records the first answer per (subject kind, id, revision, decider) and refuses a stale revision with `stale_subject`; with two deciders answering concurrently it records both and decides only after the second consent; a refusal sends the tasks to `negotiating`; two deciders consenting to different tension options decide nothing and send the tasks to `negotiating`; a decision after `decision_deadline` is `deadline_exceeded`, and an undecided subject at its deadline returns its tasks to `negotiating` with no commitment; a replan supersedes the task's active commitment and needs a new commitment and a fresh owner approval; a second answer from the same decider is not recorded (`not_authorized`); keeps a consent open across a disconnect; refuses a decision whose `consent_sig` the pinned owner key does not verify | Host |
| C-16 | Gives every derived output the narrowest scope of its sources: the intersection of the resolved principal sets at derivation time, roles resolved to the members holding them then, `self` resolved to the source sender's owner, an empty intersection becoming `host`, any unprojected source with a redaction list making the output `host`, projected sources contributing none; reproduces `spec/vectors/scope.json` | Host |
| C-17 | Renders every catalog component from AG-UI snapshots and deltas | Surface |
| C-18 | Shows a consent request and records only the person's own answer | Surface |
| C-19 | Shows nothing outside the viewer's scope, from the first snapshot on | Surface |
| C-20 | Applies the authorization matrix: each row of Target authorization is rejected with `not_authorized` (or `not_a_decider`) when the sender is the wrong party or the object is not its own, even where the scope allows it; host-only types are rejected from members; a first-time `join` from an invited participant is accepted (not `unknown_participant`); a `match` round for another `task_id`, or for a task not `negotiating`, is rejected; a `commit` reusing a `commitment_id` is `not_authorized` | Host |
| C-21 | Counts a member's offers and commitments only after it accepted the current charter revision and suspends its open commitments on a new revision | Host |

The runner prints a signed report that implementers may publish with their release.
