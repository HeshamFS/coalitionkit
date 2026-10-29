# SPDX-License-Identifier: Apache-2.0
"""Run the server or administer a running instance."""

import argparse
import json
import logging
from pathlib import Path

import httpx
import uvicorn

from .app import create_server
from .settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser(prog="coalitionkit-server")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("serve")
    create = commands.add_parser("init-coalition")
    create.add_argument("--charter", type=Path, required=True)
    invite = commands.add_parser("invite")
    invite.add_argument("coalition")
    invite.add_argument("participant")
    commands.add_parser("status")
    args = parser.parse_args()
    settings = Settings()
    if args.command == "serve":
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger = logging.getLogger("coalitionkit.server")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
        uvicorn.run(
            create_server(settings),
            host=settings.bind_host,
            port=settings.bind_port,
            access_log=False,
            log_level="warning",
        )
        return
    if settings.admin_token is None:
        parser.error("COALITIONKIT_ADMIN_TOKEN is required")
    with httpx.Client(
        base_url=settings.public_base_url,
        headers={"Authorization": "Bearer " + settings.admin_token.get_secret_value()},
    ) as client:
        if args.command == "init-coalition":
            response = client.post("/admin/coalitions", json=json.loads(args.charter.read_text()))
        elif args.command == "invite":
            response = client.post(
                f"/admin/coalitions/{args.coalition}/invitations",
                json={"participant": args.participant},
            )
        else:
            response = client.get("/admin/status")
        response.raise_for_status()
        print(json.dumps(response.json()))
