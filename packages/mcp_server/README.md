# CoalitionKit MCP server

Lets any MCP host join a coalition with the same rights as an A2A member. A member reaches the host at `<host>/mcp` with its viewer token as a bearer token, and sees only its own view.

When a tool needs a person's decision, the host asks them inside the call using MCP elicitation. Only their answer is signed, and no tool argument can stand in for it.

See [Bring your own agent over MCP](https://github.com/HeshamFS/coalitionkit/blob/main/docs/guides/mcp-agents.md) and the [list of tools](https://github.com/HeshamFS/coalitionkit/blob/main/docs/reference/mcp.md).

Part of [CoalitionKit](https://github.com/HeshamFS/coalitionkit).
