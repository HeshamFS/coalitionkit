# Contributing to CoalitionKit

Open an issue describing the behavior you want to change, then send a focused pull
request with a reproducible example and relevant tests. Security reports belong in
the private channel described in [SECURITY.md](https://github.com/HeshamFS/coalitionkit/blob/main/SECURITY.md).

## Development

Use Python 3.12 or newer, uv 0.13.6, Node 22.15.0 and npm 11.10.0. Dependency versions are
recorded in `uv.lock` and `apps/web/package-lock.json`. PSI tests additionally need
libsodium 1.0.18 or newer; on Ubuntu install `libsodium23`.

```sh
uv sync --locked
uv run python tools/build_web.py
uv run python tools/check.py
npm --prefix apps/web run lint
npm --prefix apps/web run test:ci
uv run python tools/check_workflows.py
uv run python tools/smoke_install.py
```

`tools/build_web.py` installs the locked web dependencies, type-checks and builds
the room and MCP App, and stages protocol data into the Python packages. Node is
needed only for developing or building a release. Wheel and source-distribution
installations use the already built assets. Run this step again after changes to
`spec/` or the web application. `--skip-install` reuses existing `node_modules`.

The smoke check builds every package, installs only wheels in a temporary venv
outside the checkout, starts and stops the CLI, and checks HTTP responses from two
working directories. Pass `--wheelhouse /path/to/wheels` for an offline dependency
source. Ordinary smoke runs download third-party wheels before the offline install.

Keep source files below 500 lines and functions below 120 lines. Add the Apache-2.0
SPDX header to new source files. Core code must remain domain-agnostic. Put domain
content in Discipline Packs and keep protocol changes consistent with `spec/`.
Tests that need a model key are skipped without it; never describe those as passed.
Keep credentials out of commits, fixtures, issue reports and screenshots.

## Release preparation

All Python packages use version 0.1.0 and exact versions for internal dependencies.
The `coalitionkit` distribution aggregates the 16 core distributions. Framework
extras use `coalitionkit-langgraph` and `coalitionkit-langchain`, built the same way.
`zstandard`, which `langchain-core` needs through `langsmith`, has no Python 3.15 wheel,
so on 3.15 those two need a C compiler. The workspace overrides it, because it is only
used to compress tracing uploads.
The aggregate is outside the development workspace lock so its optional framework
dependencies do not prevent core development before those packages are available.

Build each package after staging resources:

```sh
uv build packages/coalitionkit --no-sources
```

Repeat for each directory under `packages/`. Release CI does this automatically.
No tags or automatic publishing triggers are used. The manual release workflow
builds and checks by default; publishing additionally requires its `publish` input,
the `main` branch, and the GitHub `pypi` environment. Before first publication,
configure a PyPI trusted publisher for **each** distribution with owner `HeshamFS`,
repository `coalitionkit`, workflow `release.yml`, and environment `pypi`. Protect
that environment with a required reviewer. No API token belongs in this repository.
