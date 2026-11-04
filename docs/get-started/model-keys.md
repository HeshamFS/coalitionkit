# Model keys

No key is needed to try the room. Add keys to use real models.

```sh
export COALITIONKIT_META_API_KEY=...
export COALITIONKIT_BASETEN_API_KEY=...
coalitionkit up
```

The host reads keys from the environment. It never prints or saves them, and they never appear in logs or errors.

## Which model does what

| Role | Default model | Does |
|---|---|---|
| Gardener | `muse-wonder-1.0` | Reads the goal, and names and explains plans. It never builds them: fixed rules do. |
| Hosted agent | `muse-spark-1.3` | Asks your questions, makes offers, routes what you say. |
| Composer | `muse-spark-1.3` | Lays out results from the closed catalog. |
| Steward audit | `meta-models/muse-spark-open-1026` on Baseten | Reviews each message. It is a different model from the agents on purpose. |
| Vault | `muse-glimmer` on local Ollama | Used by a local vault. |

Change a model with its setting, such as `COALITIONKIT_COMPOSER_MODEL`. All settings are in [Environment and settings](../reference/settings.md).

## What a room costs

The room shows the cost it measured while it runs. In our test runs, a two or three person room cost about $0.10 to $0.25 for the host's own model calls. Yours will differ with the goal, the models and the prices. An agent you bring yourself pays for its own model.

## When a call fails

Every model step has a rule-based fallback, so a failed call does not stop the room. The screen shows **model** or **rules** beside what each one made.
