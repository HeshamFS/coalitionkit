# CoalitionKit local start

From the repository root:

```sh
uv run coalitionkit up
```

The host binds only to 127.0.0.1. Open the printed address and say what needs doing
in one sentence. You check the draft, open the room, share its code, and enter.
The printed `/mcp` URL is for hosts. Ctrl+C shuts down the server.

Options: `--no-web`, `--port 8000`, `--data-dir PATH`, `--demo`, `--members 3`,
and `--reset`.

`--demo` also creates a scripted coalition. For each printed
`Sign in: p1 ... Viewer token: TOKEN` line, open its `/signin` URL, paste only `TOKEN`
into **Viewer token**, then select **Continue**. Use a separate browser tab for each
participant. The room stores the token in that tab. Save the printed tokens to sign in
again after restarting. The demo is created once per data directory. Later starts reuse
its members and credentials; they do not print new tokens. `--reset` creates a fresh
demo and credentials.

State lives in `./.coalitionkit/`: SQLite, the host key, private `admin.token`,
and the chosen port. Restarts reuse that port because it identifies the host.
Use a new data directory to change ports. `--reset` removes only a directory
with this command's matching ownership marker; it refuses links and unowned
folders. Do not reset a directory while another host uses it.

No model key is needed. Without one the room runs on built-in rules and says so.
`COALITIONKIT_META_API_KEY` is read by the server from the environment;
the command never displays or saves it. The admin token is never displayed.

An installed package carries the room's files. From a source checkout, `apps/web/dist`
is served on the host origin, and npm builds it when it is missing or older than its
source, installing missing dependencies with `npm --prefix apps/web ci`. If npm is
missing or the build fails, `up` stops and says why. Use `--no-web` to skip the room.
API routes stay on the same origin.

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
