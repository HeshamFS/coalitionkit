# CoalitionKit Core

An open protocol and a Python runtime for groups of people whose AI agents, from any vendor, work toward one goal together. Each person keeps their own data private, sees their own live screen, and signs every decision that binds them.

The protocol is an extension to [A2A 1.0](https://a2a-protocol.org). The reference host keeps one signed, append-only log per Coalition and gives each member a live view of only what their scope allows. Members can take part from a web room, a phone message thread, a glasses lens or any MCP host.

Status: v0.1, pre-release. The spec is a draft and will change in response to implementers until v1.0 freezes it.

## Start it

You need [uv](https://docs.astral.sh/uv/) and, for the web room, Node 22.

```sh
git clone https://github.com/HeshamFS/coalitionkit
cd coalitionkit
uv run coalitionkit up
```

`up` starts a local host and the web room on 127.0.0.1, creates a demo Coalition with three members, and prints one viewer token per member. Open the printed address, paste a token, and you are in the room as that member. No model key is needed to start; model features use `COALITIONKIT_META_API_KEY` when it is set. Details: [packages/cli/README.md](packages/cli/README.md).

To reach the same Coalition from Claude Code, Claude Desktop, Codex, Grok or Antigravity, see [docs/mcp-hosts.md](docs/mcp-hosts.md).

## What has been measured

Eight acceptance tests cover interop, privacy, generative UI, ripple, scale, the Mint, chaos and cost. All eight pass; the latest results are in [docs/scorecard/2026-10-30.md](docs/scorecard/2026-10-30.md). A few headline numbers from that run:

- 0 of 2,000 planted canaries found outside the vault
- 700 agents in 51 Coalitions with 0 lost events; send p95 0.62 s into a 200-agent Coalition
- a dropped database connection heals in 0.11 s without a restart, with 0 lost or duplicated events

## The pieces

| Package | What it does |
|---|---|
| `contracts` | Envelope, receipt and consent types, JSON Schema validation, JWS signing, scope resolution |
| `runtime` | `CoalitionHost`: the signed log, lifecycle rules, projections per viewer, SQLite or PostgreSQL |
| `edges` | A2A transport: agent cards, the member client, the coalition extension on the wire |
| `vault` | Each member's private data, answered only by typed queries and private set intersection |
| `steward` | The independent checker: fixed policies first, then a model audit of what each recipient would see |
| `server` | The reference host: A2A, MCP, the live feed, admin routes, WhatsApp |
| `mcp_server` | The MCP tools and the MCP App view a member's host uses |
| `surfaces` | The view catalog and its renderers for the room, the lens and the message door |
| `channels` | Message channels, starting with WhatsApp |
| `mint` | Turns a short video and voice note into a policy-checked MCP server for a shared resource or device |
| `gardener` | Deterministic planning: turns needs and offers into plans the deciders sign |
| `models` | The model gateway, media client, price table and cost meter |
| `packs` | Discipline packs: loaded, validated and signed as data, never code in the core |
| `conformance` | The black-box conformance runner: `coalitionkit conform --target <card-url> --level <level>` |
| `cli` | `coalitionkit up`, `conform` and `server` |
| `acceptance` | The eight acceptance tests and the scorecard |
| `apps/web` | The web room and the lens |

The core holds no scenario or discipline data; that lives in packs and examples. `tools/check.py` enforces it.

## Spec and conformance

- Protocol: [spec/coalition-protocol-v0.1.md](spec/coalition-protocol-v0.1.md)
- JSON Schemas: [spec/schemas/coalition/v0/](spec/schemas/coalition/v0/)
- Shared test vectors: [spec/vectors/](spec/vectors/)
- Design decisions: [docs/adr/](docs/adr/)

An implementation claims conformance at the member, vault, host or surface level by passing that level's tests with the published runner, which prints a signed report.

## Develop

```sh
uv sync
uv run python tools/check.py          # lint, types, import boundaries, tests, the core rule
npm --prefix apps/web ci && npm --prefix apps/web test
```

Live tests run only with `COALITIONKIT_LIVE=1` and a key, and are reported as not run otherwise.

## License

Apache 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
