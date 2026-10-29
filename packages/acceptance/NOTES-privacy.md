# Notes from acceptance test 2 (privacy canaries)

Nothing in another package was changed. Every finding has an id, an exact path and a minimal
reproducing test in `tests/test_privacy_findings.py`, marked `xfail(strict=True)` with the same id.
A fix elsewhere makes the test pass unexpectedly, which fails the suite until the marker is removed.

Result of the runs themselves: no canary of the 20 planted per run was found outside its vault,
redacted field, private scope, plan assignment or PSI input on any surface the host sends out
(PR variant 10 runs; full variant 100 runs: 2,000 canaries, 0 found, 19,600 deliveries scanned; live variant 5 runs). The only leak is PRIV-1, which
needs a model that repeats what it was asked to judge; it is not part of the 0 above because the
runs use a model that answers honestly.

## PRIV-1: a Steward verdict repeats whatever the model puts in its reason (leak)

- Surface: Steward verdict text (`VerdictBody.explain`, `VerdictBody.policy_id`).
- Event: any logged event that the Steward audits and the model answers with a stricter action
  (here: an `observe` with `scope.redact = ["payload.content"]` and audience `coalition`).
- Field: `explain` is the model's `reason`; `policy_id` is the model's `policy_id`
  (`engine.py`, `_audit` then `_stricter`). Both are passed through unfiltered, `explain` capped
  at 500 characters and `policy_id` at 64.
- Path: the model audit prompt carries the unredacted payload text (the Steward sees every
  event). A model that is steered into repeating its input answers
  `{"action": "escalate", "reason": <the prompt>}`; the verdict then carries the redacted value,
  and whoever may see the event (everyone, for a coalition-wide event) may see its verdict.
  `steward_blocked` also puts `policy_id` into the error detail sent to the sender.
- Measured with the scripted worst-case model (`privacy_collect.echo_text`): 20 leaks (seed 7) across
  the 3 redacted canaries and the 4 viewers in one run. With an honest model: 0.
- Reproduce: `test_priv1_steward_verdict_text_carries_no_redacted_field`.
- Suggested fix (not applied): the Steward should never copy model text into a verdict that
  leaves the host. Use the fixed `explain` of the policy, or check the model's reason and
  `policy_id` against the payload before it is signed.

## PRIV-2: an MCP write is committed, but the tool reports `not_authorized` (bug, no leak)

- Surface: MCP tool results.
- Event: every write tool that sends with the server's default scope (`gateway.HOST_SCOPE`,
  audience `host`): `answer_question`, `make_offer`, `commit`, `report_ripple`, `report_done`,
  `leave_coalition`.
- Path: the host acknowledges an event scoped `host` to a sender outside that scope with the
  receipt alone (`accepted: null`, spec: "nothing when the sender is outside the event's
  scope"). `gateway.send` then raises `CoalitionToolError("not_authorized", "the host gave no
  acknowledgement")`. The event is in the log. The person sees an error for a write that worked.
- Reproduce: `test_priv2_mcp_write_reports_success_for_a_committed_event`
  (`report_ripple` over a real served MCP app on top of `CoalitionHost`).

## PRIV-3: the host refuses the request and response rounds of a PSI exchange (bug, no leak)

- Surface: `coalition.match` relay.
- Path: `lifecycle.State.apply` stores `requester = owner` of the `setup` message and
  `responder = body["peer"]`. The spec has the responder send `setup`, so the host records the
  responder as `requester`. `rules._match` then requires `request` from that party and
  `response` from the peer, which the protocol forbids: the vault `Requester` sends `request`,
  the vault `Responder` sends `response`.
- Measured: `setup` is accepted; `request` and `response` are refused `not_authorized`
  (`PrivacyWorld.psi.refusals == ["request:not_authorized", "response:not_authorized"]`).
- The vault code itself is right: the two parties complete the exchange locally and the
  requester learns exactly the overlap (checked in every run). The blobs are scanned on the
  `psi_blob` surface whether the host relays them or not; none holds a canary in any encoding.
- Reproduce: `test_priv3_psi_rounds_are_relayed_in_protocol_order`.

## Not covered, and why

- The Steward is not on the host's accept path: `coalitionkit_runtime.Steward.review` is
  synchronous and `coalitionkit_steward.Steward.review` is async, so no host-side check ran with the
  real Steward. The runs call the real Steward over every logged event and every derived output
  afterwards, and scan its prompts and verdicts.
- Plan-assignment canaries are assignee IDs that no member holds, because a plan whose tasks are
  scoped narrower than the Coalition is refused (the derived scope may not widen). What the runs
  test is that the per-viewer projection of `coalition.propose` removes other assignees on every
  surface.
- PostgreSQL was not used; the runs use SQLite.
- Number-range probing: a vault answers `yes`, `no` or a registered tariff, never a value, so
  binary search over a limit yields at most the same bit each time. The runs record 60 probe
  answers per victim per adversary and scan them; no canary number appears.

## PRIV-4: the Steward's model audit receives private and redacted text (decision pending)

- Surface: model prompts of the Steward (`engine.py`, `_audit_messages`).
- The Steward's model audit receives private and redacted text and sends it to a hosted model.
  Decision pending with the owner. Options: audit only projections; keep private content to
  deterministic policies; or run the Steward model on a no-retention or self-hosted endpoint.
- Measured, not counted as a leak and not as an allowed sighting: the scanners report these as
  `sent_to_models.steward_model` (55 canaries over 5 live runs, where the Steward saw redacted and
  private-scope events). Prompts to the hosted agent of a member the canary's scope entitles are
  reported apart as `sent_to_models.member_agent`; that is legitimate (a member's own agent sees
  what that member may see) and is documented here as such.
- Related: PRIV-1 is the other half, the verdict text coming back out.
