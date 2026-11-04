# CoalitionKit surfaces

What each viewer sees:

- the AG-UI feed at `GET /v1/feed`, which opens with a state snapshot and sends only what the viewer's scope allows,
- the agent stream at `GET /v1/agent`, and consent answers at `POST /v1/agent/answers`,
- A2UI trees: the catalog, composing, and the check every tree must pass on the host.

A model picks only catalog components, and an invalid tree never reaches a screen. See [Generative UI](https://github.com/HeshamFS/coalitionkit/blob/main/docs/concepts/generative-ui.md) and the [room feed](https://github.com/HeshamFS/coalitionkit/blob/main/docs/reference/room-feed.md).

Part of [CoalitionKit](https://github.com/HeshamFS/coalitionkit).
