# Templates and allocation

## Task templates

`templates.yaml` lists needs the Gardener may draft first from the charter:

```yaml
templates:
  - id: ladder-saturday
    title: Borrow a ladder for Saturday
    requirements: [ladder]
    ext: { tool_kind: ladder, days: 2 }
  - id: sprayer-week
    title: Borrow a paint sprayer for a week
    description: A paint sprayer for the fence, for one week.
    scope: { audience: roles, roles: [keeper, lender] }
    ext: { tool_kind: paint-sprayer, days: 7 }
```

A template can set who sees it with `scope`, and its `ext` must pass the pack's need schema.

## Allocation

`strategy` chooses how the Gardener allocates work:

```yaml
strategy: { allocation: auction, fairness: { weight: 1, max_ratio: 2, minute_value: 1 } }
```

`fairness` sets how much an even load counts, and the most one member may carry compared with another. `minute_value` turns minutes into the same units as money. In this version `auction` is the only usable strategy. See [Pack format](../../reference/pack-format.md).

Plans still come from fixed rules, and a person's own yes is what commits them. See [Plans and fairness](../../concepts/plans-and-fairness.md).
