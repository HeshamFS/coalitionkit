# A complete small pack

[`examples/packs/tool-library`](https://github.com/HeshamFS/coalitionkit/tree/main/examples/packs/tool-library) is a pack for neighbours who lend each other tools. It is small, and it uses every part of the format. Copy it and change it.

```sh
coalitionkit pack validate examples/packs/tool-library
coalitionkit pack eval examples/packs/tool-library
coalitionkit pack accept examples/packs/tool-library
```

## The manifest

`pack.yaml` names everything else:

```yaml
name: tool-library
version: 1.0.0
core: ">=0.1,<0.2"
roles:
  keeper: { label: Keeper, may: [charter, offer, decide, commit] }
  lender: { label: Lender, may: [offer, decide, commit] }
  shed: { label: Tool shed, may: [offer] }
suggest:
  keywords: [tool library, borrow tools, lend tools, ladder]
  examples: ["Share the neighbourhood tools for the weekend repair day"]
vocabulary: vocabulary.yaml
schemas:
  need: schemas/need.json
  offer: schemas/offer.json
policies:
  - policies/no-payment-details.yaml
  - policies/safety-sign-off.yaml
  - policies/redact-street-address.yaml
task_templates: templates.yaml
strategy: { allocation: auction, fairness: { weight: 1, max_ratio: 2, minute_value: 1 } }
views: views.yaml
skills: [skills/SKILL.md]
lessons: [lessons/loans.md, lessons/handover.md]
mint:
  - { template: mint/bench.json, tests: mint/bench-tests.json }
connectors:
  - { name: shed-desk, command: [python, shed_desk.py] }
evals: [evals/repair-day.yaml, evals/ladder-loan.yaml]
acceptance: acceptance.yaml
```

Only `name`, `version`, `core`, `roles` and `evals` are required.

## How a host offers a pack

With `suggest`, a host can offer the pack when someone types a goal that matches its keywords. A person can always turn it down.

## Tests

The folder's `test_contract.py` shows how to test a pack in pytest: load it, validate it, sign it, run its evals and its journey.
