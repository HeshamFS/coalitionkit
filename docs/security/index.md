# Security and privacy

CoalitionKit makes a few strong promises and has clear limits. Read both before you put anything real in a room.

## What the design guarantees

- **An agent cannot commit you.** Your consent is signed with your owner key, in a screen the model cannot draw. An agent's key cannot stand in for it, and the host refuses a decision the owner key does not verify.
- **The log cannot be quietly rewritten.** Entries are hash-linked and signed, and members keep signed receipts. An edited or shortened log is caught by a receipt someone kept.
- **Models pick only catalog components.** Every tree is checked on the host, and no HTML passes through.
- **Scopes are enforced by the host.** A derived output takes the narrowest scope of its sources.

## What it does not guarantee

- **You must trust the host with a hosted seat.** It holds the keys and the vault.
- **Your agent's model provider sees what the agent reads.** That includes your private answers.
- **The Steward checks policy, not truth.** It can miss things.
- **Version 0.1 is a draft and has had no outside security audit.**

Read the details in the [threat model](threat-model.md) and [what is private](privacy.md).

## Report a problem

Report suspected vulnerabilities privately, as described in [`SECURITY.md`](https://github.com/HeshamFS/coalitionkit/blob/main/SECURITY.md). Do not post an exploit, a secret or private data in a public issue.
