# SPDX-License-Identifier: Apache-2.0
"""Car desk business agent: joins with a signed card and offers the seats it holds.

Runs in the kit's connector container: standard library only, read-only, no capabilities.
It receives one argument, the one-use invitation link, and talks only to the host named in it.
Everything it decides is deterministic: a fixed list of vehicles, matched to needs in order.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import urllib.request
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlsplit

# One car desk, three vehicles. Prices are minor units (cents); travel time is in minutes.
VEHICLES: tuple[dict[str, Any], ...] = (
    {
        "id": "van-1",
        "destination": "Northgate",
        "departure": "2030-03-02T05:00:00Z",
        "seats": 6,
        "price": 4500,
        "travel_minutes": 60,
    },
    {
        "id": "car-2",
        "destination": "Eastport",
        "departure": "2030-03-02T04:30:00Z",
        "seats": 4,
        "price": 3200,
        "travel_minutes": 90,
    },
    {
        "id": "van-3",
        "destination": "Southfield",
        "departure": "2030-03-02T04:00:00Z",
        "seats": 6,
        "price": 2800,
        "travel_minutes": 120,
    },
)
VALID_UNTIL = "2099-01-01T00:00:00Z"
SPEND_LIMIT_CENTS = 50_000  # offers at or above this wait for a person (policy spend-needs-person)

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


def public_key(seed: bytes) -> bytes:
    h = hashlib.sha512(seed).digest()
    secret = (int.from_bytes(h[:32], "little") & ((1 << 254) - 8)) | (1 << 254)
    return _encode(_multiply(secret, _BASE))


def sign(seed: bytes, message: bytes) -> bytes:
    h = hashlib.sha512(seed).digest()
    secret = (int.from_bytes(h[:32], "little") & ((1 << 254) - 8)) | (1 << 254)
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
        "name": "Harbour car desk",
        "description": "A car desk that offers the seats it holds",
        "supportedInterfaces": [
            {"url": base + "/a2a", "protocolBinding": "JSONRPC", "protocolVersion": "1.0"}
        ],
        "version": "1.0.0",
        "capabilities": {
            "extensions": [
                {
                    "uri": "https://coalitionkit.dev/ext/coalition/v0",
                    "description": "Offers seats in Coalitions",
                    "params": {
                        "surfaces": ["web"],
                        "keys": [key],
                        "roles": ["car-desk"],
                        "vault": "hosted",
                    },
                }
            ]
        },
        "defaultInputModes": ["application/vnd.coalitionkit.envelope+json"],
        "defaultOutputModes": ["application/vnd.coalitionkit.envelope+json"],
        "skills": [
            {
                "id": "car-desk",
                "name": "Car desk",
                "description": "Holds vehicles and offers their seats",
                "tags": ["coalition"],
            }
        ],
    }
    protected = b64url(canonical({"alg": "EdDSA", "kid": "agent", "typ": "JOSE"}).encode())
    signing_input = protected + "." + b64url(canonical(card).encode())
    signature = b64url(sign(seed, signing_input.encode("ascii")))
    return {**card, "signatures": [{"protected": protected, "signature": signature}]}


# ---- What the desk offers ----
def parse_time(text: str) -> datetime:
    return datetime.fromisoformat(text).astimezone(UTC)


def arrival(vehicle: dict[str, Any]) -> datetime:
    return parse_time(vehicle["departure"]) + timedelta(minutes=int(vehicle["travel_minutes"]))


def offers_for(needs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One offer per need that a held vehicle can serve, in need order; deterministic."""
    result: list[dict[str, Any]] = []
    for index, need in enumerate(needs):
        if not all(key in need for key in ("destination", "party_size", "latest_arrival")):
            continue  # a need drafted from a sentence carries no trip details to match on
        for vehicle in VEHICLES:
            fits = (
                vehicle["destination"] == need["destination"]
                and vehicle["seats"] >= need["party_size"]
                and arrival(vehicle) <= parse_time(need["latest_arrival"])
            )
            if not fits:
                continue
            cents = int(vehicle["price"])
            result.append(
                {
                    "need": index,
                    "hold": vehicle["id"],
                    "capacity": int(need["party_size"]),
                    "cost": {"minutes": vehicle["travel_minutes"], "money": cents, "effort": "low"},
                    "valid_until": VALID_UNTIL,
                    "ext": {
                        "destination": vehicle["destination"],
                        "departure": vehicle["departure"],
                        "seats": int(need["party_size"]),
                        "price": f"EUR {cents // 100}.{cents % 100:02d}",
                    },
                    "needs_person": cents >= SPEND_LIMIT_CENTS,
                }
            )
            break
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
        print("usage: car_desk.py <invitation-link>", file=sys.stderr)
        return 2
    base = "https://car-desk.example.invalid"
    card = build_card(base, os.urandom(32))
    joined = redeem(argv[1], card, base + "/card")
    # Needs the host showed this desk are public task data; here the desk answers the pack's trips.
    needs = [
        {"destination": "Northgate", "party_size": 3, "latest_arrival": "2030-03-02T07:00:00Z"},
        {"destination": "Eastport", "party_size": 2, "latest_arrival": "2030-03-02T08:00:00Z"},
        {"destination": "Southfield", "party_size": 3, "latest_arrival": "2030-03-02T09:00:00Z"},
    ]
    print(json.dumps({"joined": joined.get("participant"), "offers": offers_for(needs)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
