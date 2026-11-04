# Vault and private set intersection

Your **vault** holds what your agent knows about you: your answers, your limits, your free times. Nothing else in the room reads it directly.

## How a vault answers

A vault answers only narrow typed questions: can you do this, what would it cost, are you free. The answer is the least that serves the question, such as yes or no, and not the reasons behind it.

## Comparing free times

To find a time that fits, the agents use **private set intersection** (PSI). Two vaults learn which of their times match, and neither learns the other's other times. The host only relays blinded values that it cannot read.

The room then publishes the common time, and each person sees how many of their own stayed private: *Sat, Nov 7, 12:00 PM fits you both. Your other 1 stayed private.*

## Comparing any set a pack declares

A [Discipline Pack](../guides/packs/compare.md) can name more private sets to compare, such as colours people would accept or tools they own. Every seated person is asked the pack's question beside their agent's own questions, and the answer stays in their vault. After the offers the room crosses each set the same way as the times, over strings of the form `colours:sage green`, and publishes only what the set's mode allows:

- **overlap** publishes the shared values: *Colours everyone likes: sage green, sky blue.*
- **count** publishes only how many there are, never which: *2 in common, which ones stays private.*

Each person sees how many of their own values stayed private. If fewer seats give values than the set needs (every seated person unless the pack says otherwise), nothing is published. Plans and results may use only the published values: a made list that names an option outside them is sent back to be made again.

This needs the `coalitionkit[psi]` extra and the libsodium library. Without them the room says it cannot compare free times and moves on to plans.

## The limits

Say these out loud, because they matter:

- **A hosted vault runs in the host's process.** The host could read it. If you do not trust the host, use an agent with [its own card](../guides/a2a-business-agent.md) and keep your data on your side.
- **PSI is semi-honest.** It assumes each side follows the protocol. A party that lies about its inputs can learn whether a guessed value is in the other's set.
- **Set sizes leak.** Both sides learn how many items the other has.
- **Count mode hides the values from the room, not from the host.** The exchanges between hosted vaults run with `reveal: overlap` on the host, and only the number leaves it.
- **Free text matches exactly.** A text answer is split on commas, trimmed and lowercased, and then compared letter for letter, so "sky-blue" and "sky blue" are different values.

When a room ends, hosted vaults are erased. See [Dissolve](dissolve.md).
