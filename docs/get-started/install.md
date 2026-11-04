# Install

CoalitionKit needs Python 3.12 or newer.

## With pip

```sh
python -m venv .venv
. .venv/bin/activate        # on Windows: .venv\Scripts\activate
pip install coalitionkit
coalitionkit up
```

The package carries the web room, so you do not need Node.

To let people compare free times without showing them, install the `psi` extra and the libsodium library (see below). Without it the room still works, skips that comparison and says so.

## From a clone

You need [uv](https://docs.astral.sh/uv/), which fetches Python for you, and Node 22 or newer for the web room.

```sh
git clone https://github.com/HeshamFS/coalitionkit
cd coalitionkit
uv run coalitionkit up
```

The first run builds the web room, which takes a minute or two. Later runs rebuild it only when its source has changed.

## Optional parts

| Extra | Adds | Needs |
|---|---|---|
| `coalitionkit[psi]` | Private set intersection, to compare free times | The libsodium library: `apt install libsodium23` on Debian or Ubuntu, `brew install libsodium` on macOS |
| `coalitionkit[postgres]` | PostgreSQL storage instead of SQLite | A PostgreSQL server |
| `coalitionkit[whatsapp]` | The [WhatsApp channel](../guides/whatsapp.md) | A WhatsApp Business account |

A clone installs what the tests need, including private set intersection.

## Check it

```sh
coalitionkit up --no-web --port 8000
```

In another terminal, `curl http://127.0.0.1:8000/healthz` answers `200`. Press Ctrl+C to stop the host.

Next: [your first room](first-room.md).
