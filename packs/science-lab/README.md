<!-- SPDX-License-Identifier: Apache-2.0 -->
# Science lab

Coordinate several labs sharing samples, instrument time and a courier toward a
Friday deadline. The auction balances offered time and cost against a per-member
fair-share cap (weight 1, max_ratio 2 hours per share unit, minute_value 1).
Represent each lab by one lab-lead seat when applying the cap across labs.

```powershell
uv run coalitionkit up --pack packs/science-lab
uv run coalitionkit pack validate packs/science-lab
uv run coalitionkit pack eval packs/science-lab --json
uv run coalitionkit pack accept packs/science-lab --json
uv run pytest -q packs/science-lab/test_contract.py
uv run python tools/check.py
```

The integrator runs the same eval and acceptance commands with `--live` and
COALITIONKIT_META_API_KEY. No pack step changes between those modes. The Mint
acceptance uses the kit's local subprocess sandbox and does not need Docker.

Lab leads charter, offer, decide and commit; technicians and couriers offer and
commit. Instruments offer only. Offer ext contains instrument, free_window and
sample_capacity. Need ext may carry sample_count and temperature_range in C. Both are optional, so a need drafted from a sentence in Genesis is valid; templates fill them.
Internal priority and cost ceiling are x-private vault fields, never offer data.

The two evals plant three independent cost-ceiling canaries each and assert a
shared Friday slot, then a replacement slot. The acceptance journey adds nine
competing offers across three labs, exact allocation and fairness assertions,
owner signatures and rejection of agent-only consent, a proved and approved Mint
reading panel, selective replanning, a blocked clinical-advice probe, and a lesson
written at Dissolve. Its three additional vault canaries must remain private.

The Mint template is a read-only temperature display with a 450 C alarm threshold.
Its tests reject writes, deletes and arguments that attempt to overwrite readings.
A person approves the signed agent and reviews its reading before changing a run.

## Frozen-kit limits

- The bare validate command does not load a catalog and refuses packs with bound
  views. Custom ordering is cut from the manifest; views.yaml retains the proposed
  catalog-only ordering for a future kit. Runtime uses default component ordering.

- The eval format supports slot decisions, not offers, auction objectives or Mint
  events. Those stronger assertions live in acceptance; the second eval alone
  does not prove that a reading caused a replan.
- Acceptance binds the selected pack through Genesis; it does not assert automatic
  suggestion. The manifest supplies the keywords for ordinary Genesis suggestion.
- Acceptance stores all vault answers privately but only its absent-member branch
  sends a feasibility answer. The slot evals exercise vault feasibility queries.
- v0.1 policies match text, not arbitrary field paths. A nonempty hazard must be
  the schema-constrained string `hazardous-shipment`, which escalates wherever
  present in a request or slot. This is deliberately broader than courier-only
  matching. Task/resource extensions are reserved and not enforced by this kit;
  put the marker on the need or offer, not solely on task metadata.
- Redaction hides the whole matching text field, not just digits. Structured core
  bid costs remain public; never encode an internal cost ceiling in those bids.
- The auction does not enforce temperature bounds, sample capacity, chronological
  windows or anneal-before-image dependencies. Joining agents must verify these
  before offering. The fixtures prove allocation, not a scientific schedule.
- Mint acceptance proves and enrolls the signed device, reads it through MCP, and
  has the lab lead submit the ripple. It does not capture a physical display or
  automatically submit a change under an instrument member identity. The kit's
  live acceptance retains this same trusted sensor fixture.

This pack never controls an instrument, authorizes hazardous transport, supplies
dosing or clinical advice, promises scientific validity, publishes a vault ceiling,
or commits on an owner's behalf. The frozen kit is unchanged. Required domain
terms already present in the kit are reported by the separation scan for the
integrator; this pack does not remove or conceal those conflicts.
