# Deploy a host

The kit does not ship a container image or a deployment template, and we have not run it in production. This page lists what a deployment has to cover.

## What you provide

| You need | Why |
|---|---|
| TLS in front of the host | Tokens and links travel in requests |
| `COALITIONKIT_PUBLIC_BASE_URL` | Set it to the public HTTPS origin. Links, cards and origin checks use it |
| `COALITIONKIT_ENV=production` | The host then refuses to start without the model keys, or with plain HTTP model addresses |
| `COALITIONKIT_ADMIN_TOKEN` | A long random value, stored as a secret |
| `COALITIONKIT_GENESIS=admin` | Starting a room needs a single-use code |
| PostgreSQL, with backups | SQLite is for one process on one machine |
| A safe place for the host key | The file at `COALITIONKIT_HOST_KEY_FILE` |
| The web room | `server serve` does not serve it. Build `apps/web` and serve `dist` on the same origin as the API |

## Before you open it

- Read [What is private](../security/privacy.md). On a shared host, the host's operator can read hosted vaults.
- Set budgets and watch model spend. A room's cost is measured and shown, but nothing here stops a host from running many rooms.
- Decide how long to keep logs. A room's end erases vaults, not the log.

Reports of problems go to the address in [the security policy](https://github.com/HeshamFS/coalitionkit/blob/main/SECURITY.md).
