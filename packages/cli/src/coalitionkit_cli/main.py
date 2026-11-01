# SPDX-License-Identifier: Apache-2.0
"""Top-level commands; optional commands are imported only when selected."""

import argparse
import importlib
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    words = list(sys.argv[1:] if argv is None else argv)
    if words and words[0] == "conform":
        try:
            command = importlib.import_module("coalitionkit_conformance.cli")
        except ModuleNotFoundError as exc:
            if exc.name not in {"coalitionkit_conformance", "coalitionkit_conformance.cli"}:
                raise
            print("The conformance package is not installed.")
            return 2
        return command.main(words[1:]) or 0
    if words and words[0] == "server":
        from coalitionkit_server.cli import main as server_main

        previous = sys.argv
        try:
            sys.argv = ["coalitionkit-server", *words[1:]]
            server_main()
        finally:
            sys.argv = previous
        return 0
    parser = argparse.ArgumentParser(prog="coalitionkit")
    commands = parser.add_subparsers(dest="command", required=True)
    up = commands.add_parser("up", help="start a local host and room")
    up.add_argument("--demo", action=argparse.BooleanOptionalAction, default=True)
    up.add_argument("--members", type=int, default=3)
    up.add_argument("--no-web", action="store_true")
    up.add_argument("--port", type=int)
    up.add_argument("--data-dir", type=Path, default=Path(".coalitionkit"))
    up.add_argument("--pack", type=Path, action="append", default=[])
    up.add_argument("--reset", action="store_true")
    up.add_argument(
        "--pace", type=float, default=2.0, help="seconds between demo steps (0 runs at once)"
    )
    commands.add_parser("conform", help="run the optional conformance suite")
    commands.add_parser("server", help="delegate to coalitionkit-server")
    args = parser.parse_args(words)
    if args.members < 1 or (args.port is not None and not 1 <= args.port <= 65535):
        parser.error("members must be positive and port must be between 1 and 65535")
    from .up import run

    try:
        return run(args)
    except KeyboardInterrupt:
        return 0
    except OSError, ValueError:
        print(
            "Could not start: check the data directory, saved port and web build.", file=sys.stderr
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
