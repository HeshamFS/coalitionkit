# coalitionkit-gardener

The Gardener's planning core: pure, deterministic Python with no model and no network.

- `model`: typed inputs (tasks, offers, vault answers, shares, PSI overlaps, ballots).
- `strategies`: `AuctionStrategy` (Contract-Net with a fairness rule), `MatchStrategy`, `VoteStrategy`.
- `plans`: up to three Pareto-optimal plans on (total cost, max share ratio, a third objective).
- `tension`: tensions for unmet hard constraints, vote ties and large trade-offs.
- `ripple`: the tasks a change invalidates, and a re-plan that leaves every other assignment alone.

The auction minimises total private cost plus lambda times the maximum ratio of assigned hours
to agreed share. A vault "no" removes a bid; the constraint itself stays in its owner's vault.
