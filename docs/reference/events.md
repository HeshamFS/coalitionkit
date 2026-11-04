# Event types

<!-- Written by tools/gen_docs.py. Edit the source, then run it again. -->

Every message is a signed envelope in the log. The full rules are in [the protocol](protocol.md).

| Type | Required payload fields | Schema |
|---|---|---|
| `coalition.answer` | `query_id`, `result` | [`answer.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/answer.json) |
| `coalition.charter` | `goal`, `roles`, `rules`, `deadline`, `deciders`, `revision`, `created_at` | [`charter.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/charter.json) |
| `coalition.commit` | `commitment_id`, `task_id`, `status` | [`commit.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/commit.json) |
| `coalition.decide` | `subject`, `choice`, `consent`, `decided_at`, `consent_sig` | [`decide.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/decide.json) |
| `coalition.dissolve` | `reason`, `skills_written` | [`dissolve.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/dissolve.json) |
| `coalition.done` | `task_id`, `evidence` | [`done.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/done.json) |
| `coalition.join` | `card_url`, `owner_key`, `owner_proof`, `roles_requested`, `surfaces`, `vault` | [`join.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/join.json) |
| `coalition.leave` |  | [`leave.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/leave.json) |
| `coalition.match` | `match_id`, `task_id`, `peer`, `round`, `blob`, `reveal` | [`match.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/match.json) |
| `coalition.need` | `need_id`, `description`, `requirements`, `window` | [`need.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/need.json) |
| `coalition.observe` | `source`, `content` | [`observe.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/observe.json) |
| `coalition.offer` | `offer_id`, `target`, `capacity`, `cost`, `valid_until` | [`offer.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/offer.json) |
| `coalition.propose` | `proposal_set_id`, `plans`, `decision_deadline` | [`propose.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/propose.json) |
| `coalition.query` | `query_id`, `kind`, `subject` | [`query.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/query.json) |
| `coalition.receipt` | `coalition_id`, `seq`, `head_hash` | [`receipt.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/receipt.json) |
| `coalition.ripple` | `change`, `invalidates` | [`ripple.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/ripple.json) |
| `coalition.scope` | `audience` | [`scope.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/scope.json) |
| `coalition.tension` | `tension_id`, `revision`, `task_ids`, `options`, `tradeoffs`, `deciders`, `decision_deadline` | [`tension.json`](https://github.com/HeshamFS/coalitionkit/blob/main/spec/schemas/coalition/v0/tension.json) |
