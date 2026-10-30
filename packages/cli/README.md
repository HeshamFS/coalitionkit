# CoalitionKit local start

From the repository root:

```sh
uv run coalitionkit up
```

The host binds only to 127.0.0.1. For each printed `Sign in: p1 ... Viewer token: TOKEN`
line, open its root URL (`http://127.0.0.1:PORT/`), paste only `TOKEN` into
**Viewer token** on the room's sign-in screen, then select **Continue**.
Use a separate browser tab for each participant. The room stores the token in
that tab. Save the printed tokens to sign in again after restarting.
The printed `/mcp` URL is for hosts. Ctrl+C shuts down the server.

Options: `--no-web`, `--port 8000`, `--data-dir PATH`, `--members 3`,
`--demo` (default), `--no-demo`, and `--reset`.
The demo is created once per data directory. Each member's invitation is redeemed
and a signed join establishes hosted membership before their viewer token is printed.
Later starts report that the demo already exists and reuse its members and credentials;
they do not print new tokens. `--reset` creates a fresh demo and credentials.

State lives in `./.coalitionkit/`: SQLite, the host key, private `admin.token`,
and the chosen port. Restarts reuse that port because it identifies the host.
Use a new data directory to change ports. `--reset` removes only a directory
with this command's matching ownership marker; it refuses links and unowned
folders. Do not reset a directory while another host uses it.

No model key is needed to start and sign in. Model features require configured
keys. `COALITIONKIT_META_API_KEY` is read by the server from the environment;
the command never displays or saves it. The admin token is never displayed.

An existing `apps/web/dist` is served on the host origin. Otherwise npm builds
it once, installing missing dependencies with `npm --prefix apps/web ci`.
Without npm (or after a failed build), the host runs without the room.
Use `--no-web` to skip the build. API routes stay on the same origin.

```sh
uv run coalitionkit server status
uv run coalitionkit conform --help
```

`server` delegates to the existing server CLI (including its environment
configuration). `conform` requires the optional conformance package.

Verification: `uv run pytest packages/cli -q` starts a real subprocess,
checks health within 15 seconds, reads authenticated feed snapshots and agent SSE
frames with printed credentials, verifies restart persistence, and signals shutdown.
The static-mount and Room wrapper checks exercise same-origin API routing and
verify that one member cannot see another member's self-scoped observation.
No browser automation or live model call is part of this check.
