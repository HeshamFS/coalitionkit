# Python API

<!-- Written by tools/gen_docs.py. Edit the source, then run it again. -->

The API each package exports. The `coalitionkit` package installs all of them.

| Package | Module | What it holds |
|---|---|---|
| [`contracts`](contracts.md) | `coalitionkit_contracts` | Envelope, payload models, signing, scope and schema validation. |
| [`runtime`](runtime.md) | `coalitionkit_runtime` | The signed log, lifecycle rules and the projection for each viewer. |
| [`edges`](edges.md) | `coalitionkit_edges` | The A2A transport: cards, the member client and the host edge. |
| [`vault`](vault.md) | `coalitionkit_vault` | Private data, typed queries and private set intersection. |
| [`steward`](steward.md) | `coalitionkit_steward` | The independent checker: fixed policies, then a model audit. |
| [`gardener`](gardener.md) | `coalitionkit_gardener` | Deterministic planning from needs and offers. |
| [`models`](models.md) | `coalitionkit_models` | The model gateway, price table and cost meter. |
| [`surfaces`](surfaces.md) | `coalitionkit_surfaces` | The closed catalog and its renderers. |
| [`server`](server.md) | `coalitionkit_server` | The reference host and the room engine. |
| [`mcp_server`](mcp_server.md) | `coalitionkit_mcp` | The MCP tools and the MCP App view. |
| [`channels`](channels.md) | `coalitionkit_channels` | Message channels. |
| [`mint`](mint.md) | `coalitionkit_mint` | Turns a short recording into a policy-checked MCP server. |
| [`packs`](packs.md) | `coalitionkit_packs` | Discipline Packs: loading, validation and signing. |
| [`conformance`](conformance.md) | `coalitionkit_conformance` | The black-box conformance runner. |
| [`acceptance`](acceptance.md) | `coalitionkit_acceptance` | Acceptance runners for the kit. |
| [`cli`](cli.md) | `coalitionkit_cli` | The `coalitionkit` command. |
| [`langchain`](langchain.md) | `coalitionkit_langchain` | A room's actions as LangChain tools. |
| [`langgraph`](langgraph.md) | `coalitionkit_langgraph` | A graph as a seat, with an interrupt where a person must consent. |
