# SPDX-License-Identifier: Apache-2.0
"""Tool shed connector, the first half: sign a card, redeem the invitation, work out the offers.

It stops there and prints what it would offer. It does not send a join or an offer, so running
it spends the invitation. A connector that does real work goes on to send signed messages.

Runs in the kit's connector container: standard library only, read-only, no capabilities.
It receives one argument, the one-use invitation link, and talks only to the host named in it.
It never sees host settings, keys or any member's vault.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import urllib.request
from typing import Any
from urllib.parse import urlsplit

SHELF: tuple[dict[str, Any], ...] = (
    {"id": "ladder-1", "tool_kind": "ladder", "condition": "good", "minutes": 20},
    {"id": "drill-1", "tool_kind": "drill", "condition": "new", "minutes": 15},
)
VALID_UNTIL = "2099-01-01T00:00:00Z"

# ---- Ed25519 signing (RFC 8032), written out because the container has no crypto library ----
_P = 2**255 - 19
_Q = 2**252 + 27742317777372353535851937790883648493
_D = -121665 * pow(121666, _P - 2, _P) % _P
_I = pow(2, (_P - 1) // 4, _P)
Point = tuple[int, int, int, int]


def _recover_x(y: int) -> int:
    xx = (y * y - 1) * pow(_D * y * y + 1, _P - 2, _P) % _P
    x = pow(xx, (_P + 3) // 8, _P)
    if (x * x - xx) % _P:
        x = x * _I % _P
    return _P - x if x % 2 else x


def _add(a: Point, b: Point) -> Point:
    t1 = (a[1] - a[0]) * (b[1] - b[0]) % _P
    t2 = (a[1] + a[0]) * (b[1] + b[0]) % _P
    t3 = a[3] * 2 * _D * b[3] % _P
    t4 = a[2] * 2 * b[2] % _P
    e, f, g, h = t2 - t1, t4 - t3, t4 + t3, t2 + t1
    return (e * f % _P, g * h % _P, f * g % _P, e * h % _P)


def _multiply(scalar: int, point: Point) -> Point:
    result: Point = (0, 1, 1, 0)
    while scalar:
        if scalar & 1:
            result = _add(result, point)
        point = _add(point, point)
        scalar >>= 1
    return result


def _encode(point: Point) -> bytes:
    zi = pow(point[2], _P - 2, _P)
    x, y = point[0] * zi % _P, point[1] * zi % _P
    return (y | ((x & 1) << 255)).to_bytes(32, "little")


_BY = 4 * pow(5, _P - 2, _P) % _P
_BX = _recover_x(_BY)
_BASE: Point = (_BX, _BY, 1, _BX * _BY % _P)


def _digest(data: bytes) -> int:
    return int.from_bytes(hashlib.sha512(data).digest(), "little")


def _secret(seed: bytes) -> tuple[bytes, int]:
    h = hashlib.sha512(seed).digest()
    return h, (int.from_bytes(h[:32], "little") & ((1 << 254) - 8)) | (1 << 254)


def public_key(seed: bytes) -> bytes:
    return _encode(_multiply(_secret(seed)[1], _BASE))


def sign(seed: bytes, message: bytes) -> bytes:
    h, secret = _secret(seed)
    pub = _encode(_multiply(secret, _BASE))
    r = _digest(h[32:] + message) % _Q
    commitment = _encode(_multiply(r, _BASE))
    k = _digest(commitment + pub + message) % _Q
    return commitment + ((r + k * secret) % _Q).to_bytes(32, "little")


# ---- Signed card ----
def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def canonical(value: Any) -> str:
    """JSON canonical form (RFC 8785) for the card: sorted keys, no spaces, no floats."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def build_card(base: str, seed: bytes) -> dict[str, Any]:
    key = {"crv": "Ed25519", "kty": "OKP", "x": b64url(public_key(seed)), "kid": "agent"}
    card: dict[str, Any] = {
        "name": "Corner tool shed",
        "description": "A tool shed that offers the tools on its shelf",
        "supportedInterfaces": [
            {"url": base + "/a2a", "protocolBinding": "JSONRPC", "protocolVersion": "1.0"}
        ],
        "version": "1.0.0",
        "capabilities": {
            "extensions": [
                {
                    "uri": "https://coalitionkit.dev/ext/coalition/v0",
                    "description": "Offers tools in Coalitions",
                    "params": {
                        "surfaces": ["web"],
                        "keys": [key],
                        "roles": ["shed"],
                        "vault": "hosted",
                    },
                }
            ]
        },
        "defaultInputModes": ["application/vnd.coalitionkit.envelope+json"],
        "defaultOutputModes": ["application/vnd.coalitionkit.envelope+json"],
        "skills": [
            {
                "id": "shed",
                "name": "Tool shed",
                "description": "Holds tools and offers them for loan",
                "tags": ["coalition"],
            }
        ],
    }
    protected = b64url(canonical({"alg": "EdDSA", "kid": "agent", "typ": "JOSE"}).encode())
    signing_input = protected + "." + b64url(canonical(card).encode())
    signature = b64url(sign(seed, signing_input.encode("ascii")))
    return {**card, "signatures": [{"protected": protected, "signature": signature}]}


# ---- What the shed offers ----
def offers_for(needs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One offer per request the shelf can serve, in request order; deterministic."""
    result: list[dict[str, Any]] = []
    for index, need in enumerate(needs):
        item = next((i for i in SHELF if i["tool_kind"] == need.get("tool_kind")), None)
        if item is None:
            continue
        result.append(
            {
                "need": index,
                "hold": item["id"],
                "capacity": 1,
                "cost": {"minutes": item["minutes"], "money": 0, "effort": "low"},
                "valid_until": VALID_UNTIL,
                "ext": {"tool_kind": item["tool_kind"], "condition": item["condition"]},
            }
        )
    return result


def redeem(invitation_link: str, card: dict[str, Any], card_url: str) -> dict[str, Any]:
    parts = urlsplit(invitation_link)
    token = parts.fragment
    if not token or not parts.scheme or not parts.netloc:
        raise ValueError("invitation must be a link with a one-use fragment")
    request = urllib.request.Request(
        f"{parts.scheme}://{parts.netloc}/invitations/redeem",
        data=json.dumps({"invitation": token, "card_url": card_url, "card": card}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: shed_desk.py <invitation-link>", file=sys.stderr)
        return 2
    base = "https://shed.example.invalid"
    card = build_card(base, os.urandom(32))
    joined = redeem(argv[1], card, base + "/card")
    # The requests are public task data; here the shed answers a fixed list of them.
    needs = [{"tool_kind": "ladder"}, {"tool_kind": "drill"}, {"tool_kind": "paint-sprayer"}]
    print(json.dumps({"joined": joined.get("participant"), "offers": offers_for(needs)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
