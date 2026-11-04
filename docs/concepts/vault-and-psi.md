# Vault and private set intersection

Your **vault** holds what your agent knows about you: your answers, your limits, your free times. Nothing else in the room reads it directly.

## How a vault answers

A vault answers only narrow typed questions: can you do this, what would it cost, are you free. The answer is the least that serves the question, such as yes or no, and not the reasons behind it.

## Comparing free times

To find a time that fits, the agents use **private set intersection** (PSI). Two vaults learn which of their times match, and neither learns the other's other times. The host only relays blinded values that it cannot read.

The room then publishes the common time, and each person sees how many of their own stayed private: *Sat, Nov 7, 12:00 PM fits you both. Your other 1 stayed private.*

This needs the `coalitionkit[psi]` extra and the libsodium library. Without them the room says it cannot compare free times and moves on to plans.

## The limits

Say these out loud, because they matter:

- **A hosted vault runs in the host's process.** The host could read it. If you do not trust the host, use an agent with [its own card](../guides/a2a-business-agent.md) and keep your data on your side.
- **PSI is semi-honest.** It assumes each side follows the protocol. A party that lies about its inputs can learn whether a guessed value is in the other's set.
- **Set sizes leak.** Both sides learn how many items the other has.
- **The room compares time slots only.** The PSI code takes any strings, but the room uses it for times.

When a room ends, hosted vaults are erased. See [Dissolve](dissolve.md).
