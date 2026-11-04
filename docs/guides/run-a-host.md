# Run and configure a host

There are two ways to run a host.

| | `coalitionkit up` | `coalitionkit server serve` |
|---|---|---|
| For | Trying it on your computer | A server others reach |
| Listens on | `127.0.0.1` only | `COALITIONKIT_BIND_HOST` and `COALITIONKIT_BIND_PORT` |
| Web room | Yes | No, API and MCP only |
| Starting a room | Open to this computer | Set by `COALITIONKIT_GENESIS` |
| Room engine | On | Set by `COALITIONKIT_ROOM_ENGINE`, off by default |
| Settings | Its options, plus model keys | All [environment settings](../reference/settings.md) |

## `coalitionkit up`

```sh
coalitionkit up --port 8000 --data-dir ./room-data
```

State lives in `./.coalitionkit` unless you choose otherwise: SQLite, the host key, a private `admin.token` and the port. The port is kept because it is part of the host's identity, so to change it use a new data folder.

`--pack FOLDER` installs a [Discipline Pack](packs/index.md), and can repeat. `--demo` also creates a scripted Coalition and prints viewer tokens for it. It uses an older room view. `--reset` starts over, removing only a folder it made.

## `coalitionkit server serve`

```sh
export COALITIONKIT_PUBLIC_BASE_URL=https://rooms.example
export COALITIONKIT_ADMIN_TOKEN=...
export COALITIONKIT_GENESIS=admin
export COALITIONKIT_ROOM_ENGINE=on
export COALITIONKIT_META_API_KEY=...
export COALITIONKIT_BASETEN_API_KEY=...
coalitionkit server serve
```

`COALITIONKIT_GENESIS` decides who can start a room:

| Value | Who can start one |
|---|---|
| `off` | Nobody through the room API. The default. Use the admin API instead |
| `local` | This computer, without a code. A code that is sent must be valid |
| `admin` | Anyone holding a single-use start code |

The admin commands use `COALITIONKIT_ADMIN_TOKEN` and `COALITIONKIT_PUBLIC_BASE_URL`:

```sh
coalitionkit server init-coalition --charter charter.json
coalitionkit server invite COALITION_ID p1
coalitionkit server status
```

## Storage

SQLite by default. For PostgreSQL, install `coalitionkit[postgres]` and set `COALITIONKIT_STORE` to its address. The store holds the signed log and hosted vaults, so protect it like a credential.

## Keys

The host creates its signing key at `COALITIONKIT_HOST_KEY_FILE` on first start. On Linux and macOS it must have mode `0600`. Losing it means members can no longer verify the host. Treat viewer tokens, invitation links and signing keys as credentials.
