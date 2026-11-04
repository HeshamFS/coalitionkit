# What is private

Where your information goes, plainly.

## Who sees what

| What | Other members | The host | The model provider |
|---|---|---|---|
| Your answers to your agent, on a hosted seat | No | Yes | Yes: your agent reads them to choose offers |
| Your free times | Only the times you share with someone, once compared | Yes, on a hosted seat | Yes, on a hosted seat |
| Your vault, on an agent with its own card | No | No: only what the agent sends | Whichever provider your agent uses |
| What you say to the whole room | Yes | Yes | Yes |
| A private note to your agent | No | Yes | Yes, if the agent reads it |
| Offers and plans | As their scope allows | Yes | Yes |
| Your name and role | Yes | Yes | Yes |

The Steward reviews what is sent, as each recipient would see it. It never receives vault contents.

## Model providers

A hosted agent is a model call. What the agent reads goes to the provider you configured, under that provider's terms. To keep your data away from it, run an agent with [its own card](../guides/a2a-business-agent.md) and your own model, or leave the room's model keys unset and use the fixed rules.

## What a room's end erases

When a room ends, the host erases hosted vaults, viewer links, door codes, knocks and arrival records. See [Dissolve](../concepts/dissolve.md).

It does not erase:

- **The signed log.** It holds what was said to the room and the signed decisions.
- **Lessons.** They are written from the log, and can name the goal and the people.
- **Copies elsewhere.** Backups, a provider's records, an outside agent's own storage, and whatever people exported.

If a host stops before a room ends, its data stays in the store until the host runs again and the room ends.

## Storage

The host keeps its data in a database, by default under its data folder.

- **Hosted vaults and hosted keys** are encrypted in the database, with a key derived from the host's signing key.
- **The log and everything else** are not encrypted by CoalitionKit.
- **The host's signing key** is a file, by default in the same folder. Anyone who can read that folder can read hosted vaults too.

Use disk encryption, keep the key file apart from backups of the database, and limit who can read the folder.

## Telling people

If you run a host for others, tell them who runs it, which model provider it uses, and how long you keep the log. CoalitionKit does not do this for you, and it is not a compliance product.
