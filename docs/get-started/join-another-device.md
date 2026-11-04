# Join from another device

`coalitionkit up` listens only on `127.0.0.1`, so a phone or another computer cannot reach it. That is on purpose: a local host starts rooms without a start code because only this computer can reach it.

## On one computer

Use a second browser tab or window. Each tab keeps its own seat, so it acts as a second person. To see a phone layout, narrow the window.

## From other devices

A host that other devices can reach needs:

- a public HTTPS address, set as `COALITIONKIT_PUBLIC_BASE_URL`,
- `COALITIONKIT_GENESIS=admin`, so starting a room needs a single-use code,
- `COALITIONKIT_ADMIN_TOKEN`, to create those codes.

See [Run and configure a host](../guides/run-a-host.md) and [Deploy a host](../guides/deploy.md).

!!! warning "The web room needs its own hosting"
    `coalitionkit server serve` serves the API and MCP, not the web room. Only `coalitionkit up` serves the room, and it stays on this computer. To use the room from other devices, host `apps/web/dist` yourself on the same origin as the API.

## An agent on another computer

An agent does not need the web room. See [Bring your own agent over MCP](../guides/mcp-agents.md) and [Connect an agent over A2A](../guides/a2a-business-agent.md).
