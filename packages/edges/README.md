# CoalitionKit edges

The A2A edge of a coalition. `coalitionkit_edges.a2a` holds:

- the host's FastAPI app, with its signed card at the well-known path and JSON-RPC at `/a2a`,
- `MemberClient`, for an agent that joins from outside with its own card and keys,
- card identity: signed cards, pinned keys and owner binding,
- the extension on the wire, and a `FakeHost` for tests.

See [Bring your own agent over A2A](https://github.com/HeshamFS/coalitionkit/blob/main/docs/guides/a2a-business-agent.md) and [the protocol](https://github.com/HeshamFS/coalitionkit/blob/main/spec/coalition-protocol-v0.1.md).

Part of [CoalitionKit](https://github.com/HeshamFS/coalitionkit).
