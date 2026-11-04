# Mint templates and connectors

## Mint templates

A pack can give [the Mint](../mint.md) extra templates for its own rooms. Each one comes with tests, which run before a minted agent is enrolled.

```json
{
  "template": "resource",
  "name": "Workshop bench",
  "windows": [{ "start": 540, "end": 720 }],
  "duration": 60,
  "limit": 2,
  "prerequisites": []
}
```

```yaml
mint:
  - { template: mint/bench.json, tests: mint/bench-tests.json }
```

## Connectors

A connector is a program that joins a room as a business agent, such as one that reads a stock system. It runs **out of process**, started by the operator.

- It gets only a one-use invitation. It never receives host settings, keys, tokens, or access to the store or to vaults.
- It joins like any outside agent, with a signed card.

```yaml
connectors:
  - { name: shed-desk, command: [python, shed_desk.py] }
```

```sh
coalitionkit pack connectors my-pack --host URL --coalition ID          # print the commands
coalitionkit pack connectors my-pack --host URL --coalition ID --run    # run them in a container
```

[`connectors/shed-desk/shed_desk.py`](https://github.com/HeshamFS/coalitionkit/blob/main/examples/packs/tool-library/connectors/shed-desk/shed_desk.py) shows the first half, using the standard library only: it signs a card, redeems the invitation, and prints the offers it would make. **It stops there.** A connector that does real work goes on to join and send signed offers, as in [Bring your own agent over A2A](../a2a-business-agent.md).
