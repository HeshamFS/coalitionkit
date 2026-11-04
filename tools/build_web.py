# SPDX-License-Identifier: Apache-2.0
"""Stage release resources and build both web surfaces before building distributions.

Run `uv run python tools/build_web.py`. Node is a maintainer build dependency;
the resulting wheels and source distributions include the finished assets.
"""

import argparse
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def stage_spec() -> None:
    destination = ROOT / "packages/contracts/src/coalitionkit_contracts/data/spec"
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "spec", destination, dirs_exist_ok=True)
    print("Staged protocol schemas, vectors and catalog", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-install", action="store_true", help="use existing node_modules")
    parser.add_argument("--data-only", action="store_true", help="stage protocol data only")
    args = parser.parse_args()
    stage_spec()
    if args.data_only:
        return
    npm = shutil.which("npm")
    if npm is None:
        raise SystemExit("Release builds require Node >=22.12 and npm; wheel installs do not.")
    web = ROOT / "apps/web"
    if not args.skip_install:
        subprocess.run([npm, "ci", "--no-audit", "--no-fund"], cwd=web, check=True)
    subprocess.run([npm, "run", "build"], cwd=web, check=True)
    destination = ROOT / "packages/cli/src/coalitionkit_cli/web_dist"
    # Only replace this tool's generated assets, never a caller-supplied path.
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(web / "dist", destination)
    if not (destination / "index.html").is_file():
        raise SystemExit("Web build did not produce index.html")
    print("Staged web room and MCP App assets; ready to build wheels", flush=True)


if __name__ == "__main__":
    main()
