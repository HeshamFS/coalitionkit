# CoalitionKit server

From the workspace, run `uv sync`, set `COALITIONKIT_ADMIN_TOKEN` to a secret,
then run `uv run coalitionkit-server serve`. `/healthz` reports storage availability
and model route configuration (it does not call providers).

Create a coalition against that running process:

```sh
uv run coalitionkit-server init-coalition --charter packages/server/tests/fixtures/charter.json
uv run coalitionkit-server status
uv run coalitionkit-server invite <coalition-id> <participant-id>
```

The create response contains one single-use invitation per charter decider, the host
card URL and its public key. Deliver invitations and the pinned host key privately.
Redeem an invitation with `POST /invitations/redeem` and JSON
`{"invitation":"..."}` for a hosted participant, or include `card_url` and the signed
A2A `card` document for an external agent. Redemption returns a bearer token; it
does not join the coalition. Submit the owner-signed join through A2A or use MCP's
`join_coalition` tool with the hosted token. Invitations cannot be redeemed twice.

Endpoints:

- `/a2a` and `/.well-known/agent-card.json`: A2A, using the host key from the invitation.
- `/mcp`: authenticated streamable HTTP MCP; owner consent requires elicitation.
- `/v1/feed`, `/v1/agent`, `/v1/agent/answers`: authenticated viewer sessions. The
  token selects its coalition, so a caller cannot choose another coalition by URL.
- `/admin/coalitions`, `/admin/coalitions/{id}/invitations`, `/admin/status`: admin
  bearer authentication, disabled unless an admin token is configured.

All settings have the `COALITIONKIT_` prefix. `STORE` accepts `sqlite:///path` or a
Postgres URL. `HOST_KEY_FILE` defaults to the user's application data directory;
`PUBLIC_BASE_URL` defaults to `http://127.0.0.1:8000`, `BIND_HOST` to `127.0.0.1`,
and `BIND_PORT` to `8000`. `SURFACES` is a JSON array, defaulting to
`["mcp","feed","agent"]`. Model settings are supplied by `coalitionkit-models`.
Unconfigured model audits fail closed through the Steward.

Keep the same host key, public URL and store on restart. Hosted keys are encrypted
with a key derived from the host key; losing it also loses hosted signing access.
Tokens and invitations are stored as hashes. The CLI intentionally prints newly
issued invitations, while event logs contain only event ids, sequence and codes.

Only one process should own a store: the runtime's in-process bus does not synchronize
multiple workers. Postgres support uses the runtime store adapter; local-port integration
tests exercise SQLite. Live model calls are outside this package's integration tests.
