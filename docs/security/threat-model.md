# Threat model

What CoalitionKit defends against in version 0.1, and what it does not.

## Who can do what

| Party | Can | Cannot |
|---|---|---|
| A member's agent | Send what its role and scope allow, and say false things | Sign consent for its owner, send as another member, or address someone outside its scope |
| A model | Write text, and pick catalog components | Run code in a screen, answer a consent, or build a plan |
| The Steward | Stop or hold a message, or hide fields of it | Approve anything for a person, or rewrite what someone said |
| A hosted seat's host | Read that seat's vault, and sign for that seat's keys | Do this unseen by the design: it is trusted for hosted seats |
| Any host | Refuse or delay messages, and see everything sent to the room | Rewrite the log past a receipt a member kept, or sign as a member with its own keys |
| A Discipline Pack | Add words, fields, roles, policies and tests | Run code in the host, read a vault, widen a scope, or see another room |
| A connector | Join as an outside member | See host settings, keys, tokens, the store or vaults |
| A person with a viewer token | Act as that viewer | See beyond that viewer's scope |

## Defended

- **Forged or edited messages.** Each is signed, and checked against a schema and a pinned key.
- **An agent answering for a person.** Consent needs the owner key. In the browser, it is held by a trusted screen and signed only after a press and hold.
- **Stale or replayed decisions.** A decision names a revision of its subject. A stale one is refused, a duplicate returns the first answer, and the first answer per decider is the one that counts.
- **A tampered log.** The hash chain and receipts catch an edited or truncated tail, if someone kept a receipt.
- **A model drawing a fake screen.** The closed catalog has no HTML. Consent is outside what a model can draw.
- **Text pretending to be instructions.** Prompts mark goals, answers and messages as data. This reduces the risk and does not remove it. The rule that matters is that no model output can commit anyone.
- **A cross-site page starting a room.** The local start routes accept only same-origin requests from loopback.

## Not defended

- **A malicious host, for hosted seats.** It holds the keys and vaults for those seats. Use an agent with [its own card](../guides/a2a-business-agent.md) if you do not trust the host.
- **Censorship by the host.** A host can refuse or delay a message. Signatures and receipts show what happened, not what never arrived.
- **A log nobody checked.** Receipts protect only if a member keeps them and compares. A member who kept nothing cannot catch a rewrite of what they saw.
- **False claims.** Signed means someone said it, not that it is true. An agent can name a venue that does not exist.
- **A model that drifts.** The Steward's model audit is a judgement call, and text-matching policies stop patterns, not meanings. Both can miss things, and both can stop something harmless.
- **Malicious PSI inputs.** PSI in version 0.1 assumes each side follows the protocol. See [Vault and PSI](../concepts/vault-and-psi.md).
- **Denial of service.** The routes that start and join rooms have rate limits, and most others do not. A member can flood a room with duplicate offers. Run a public host behind something that limits traffic.
- **The device.** Anyone with your viewer link, browser profile or owner key is you.

## What an operator is responsible for

TLS, credential storage, access policy, backups, retention and the choice of model provider. The local command binds to loopback, so opening a host beyond this machine is a decision you make. See [Deploy a host](../guides/deploy.md).

Treat viewer tokens, invitation links, signing keys and provider keys as credentials.
