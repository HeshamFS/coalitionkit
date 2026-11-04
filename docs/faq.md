# FAQ

## Do I need an API key?

No. The room runs on fixed rules without one. Real agents need [model keys](get-started/model-keys.md).

## How much does a room cost?

In our test runs, a room of two or three people cost about $0.10 to $0.25 for the host's own model calls. The room shows what it measured while it runs. An agent you bring pays for its own model.

## Can an agent commit me to something?

No. A plan, a commitment and the charter each need your own signed yes. See [Consent](concepts/consent.md).

## Is my data private?

Other members do not see your vault. The host sees it on a hosted seat, and so does your agent's model provider. Read [what is private](security/privacy.md) before using a room for anything sensitive.

## Can I bring my own agent?

Yes. Connect it [over MCP](guides/mcp-agents.md) or [over A2A with its own card](guides/a2a-business-agent.md). Any agent framework that can speak one of these can join.

## Can people on other devices join?

`coalitionkit up` listens only on this machine, so other devices cannot reach it without more setup. See [Join from another device](get-started/join-another-device.md) and [Deploy a host](guides/deploy.md).

## Why does it need Python 3.15?

That is what the kit is built and tested on today.

## Why does the room say it cannot compare free times?

Comparing needs the `coalitionkit[psi]` extra and the libsodium library. Without them, the room moves straight on to plans. See [Troubleshooting](get-started/troubleshooting.md).

## Why is the room waiting?

Usually it is waiting for someone's yes. Plans need every decider, and the screen says whose turn it is. See [Troubleshooting](get-started/troubleshooting.md).

## Can agents search the web?

Hosted agents do not. They suggest kinds of place and what to check first, labelled as estimates. An agent you bring can use whatever tools it has.

## Is this production-ready?

Not yet. Version 0.1 is a pre-release, the protocol is a draft, and there has been no outside security audit. See the [threat model](security/threat-model.md).

## What license is it under?

Apache 2.0.
