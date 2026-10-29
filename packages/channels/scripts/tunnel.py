# SPDX-License-Identifier: Apache-2.0
"""Start a cloudflared quick tunnel to the local server and print the public webhook URL.

    uv run python packages/channels/scripts/tunnel.py --port 8000

Point the Meta app's webhook callback at the printed URL (it ends in /webhooks/whatsapp) and use
COALITIONKIT_WHATSAPP_VERIFY_TOKEN as the verify token. Press Ctrl+C to stop the tunnel.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys

URL = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
WINDOWS_DEFAULT = r"C:\Program Files (x86)\cloudflared\cloudflared.exe"


def find_cloudflared() -> str:
    return shutil.which("cloudflared") or WINDOWS_DEFAULT


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    cmd = [find_cloudflared(), "tunnel", "--url", f"http://127.0.0.1:{args.port}"]
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8"
        )
    except OSError:
        print("cloudflared not found; install it first", file=sys.stderr)
        return 1
    announced = False
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            found = URL.search(line)
            if found and not announced:
                announced = True
                print(f"Webhook callback URL: {found.group(0)}/webhooks/whatsapp", flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        proc.terminate()
    return 0 if announced else 1


if __name__ == "__main__":
    raise SystemExit(main())
