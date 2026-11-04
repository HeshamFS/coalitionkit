# SPDX-License-Identifier: Apache-2.0
"""Simulated grocer business agent: joins with a signed card and offers delivery slots.

Runs in the kit's connector container: standard library only, read-only, no capabilities.
It receives one argument, the one-use invitation link, and talks only to the host named in it.
The grocer is simulated and says so on its card. Everything it decides is deterministic: a fixed
list of delivery slots offered on the shopping need, one slot held when its offer is chosen, and
a fixed order summary when the delivery is reported done.
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

NAME = "Corner grocer (simulated)"
# Three delivery slots on the day of the dinner. Prices are minor units (cents).
SLOTS: tuple[dict[str, Any], ...] = (
    {"id": "slot-1", "window": "14:00-15:00", "fee": 400},
    {"id": "slot-2", "window": "15:00-16:00", "fee": 400},
    {"id": "slot-3", "window": "16:00-17:00", "fee": 600},
)
# The basket a dinner for six needs; fixed, so the summary is the same every run.
BASKET: tuple[tuple[str, str, int], ...] = (
    ("Seasonal vegetables", "3 kg", 900),
    ("Rice", "1 kg", 250),
    ("Chickpeas", "4 tins", 400),
    ("Fresh herbs", "3 bunches", 450),
    ("Olive oil", "1 bottle", 750),
    ("Fruit for dessert", "2 kg", 800),
)
SHOPPING_WORDS = ("shopping", "groceries", "grocer", "ingredients", "menu", "food", "buy")
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


def build_card(base: str, seed: bytes, role: str = "grocer") -> dict[str, Any]:
    key = {"crv": "Ed25519", "kty": "OKP", "x": b64url(public_key(seed)), "kid": "agent"}
    card: dict[str, Any] = {
        "name": NAME,
        "description": "A simulated grocer that offers delivery slots. Not a real shop.",
        "supportedInterfaces": [
            {"url": base + "/a2a", "protocolBinding": "JSONRPC", "protocolVersion": "1.0"}
        ],
        "version": "1.0.0",
        "capabilities": {
            "extensions": [
                {
                    "uri": "https://coalitionkit.dev/ext/coalition/v0",
                    "description": "Offers delivery slots in Coalitions (simulated business)",
                    "params": {
                        "surfaces": ["web"],
                        "keys": [key],
                        "roles": [role],
                        "vault": "hosted",
                    },
                }
            ]
        },
        "defaultInputModes": ["application/vnd.coalitionkit.envelope+json"],
        "defaultOutputModes": ["application/vnd.coalitionkit.envelope+json"],
        "skills": [
            {
                "id": "grocer",
                "name": "Grocer (simulated)",
                "description": "Offers and holds delivery slots for the shopping",
                "tags": ["coalition", "simulated"],
            }
        ],
    }
    protected = b64url(canonical({"alg": "EdDSA", "kid": "agent", "typ": "JOSE"}).encode())
    signing_input = protected + "." + b64url(canonical(card).encode())
    signature = b64url(sign(seed, signing_input.encode("ascii")))
    return {**card, "signatures": [{"protected": protected, "signature": signature}]}


# ---- What the grocer offers ----
def euro(cents: int) -> str:
    return f"EUR {cents // 100}.{cents % 100:02d}"


def basket_cents() -> int:
    return sum(price for _, _, price in BASKET)


def is_shopping(need: dict[str, Any]) -> bool:
    words = f"{need.get('title', '')} {need.get('detail', '')}".lower()
    return need.get("kind") == "list" or any(word in words for word in SHOPPING_WORDS)


def offers_for(
    needs: list[dict[str, Any]], held: frozenset[str] = frozenset()
) -> list[dict[str, Any]]:
    """One offer per shopping need, each on the next slot not yet held; deterministic."""
    result: list[dict[str, Any]] = []
    free = [slot for slot in SLOTS if slot["id"] not in held]
    for index, need in enumerate(needs):
        if not is_shopping(need) or not free:
            continue
        slot = free.pop(0)
        cents = basket_cents() + int(slot["fee"])
        result.append(
            {
                "need": index,
                "need_id": need.get("id"),
                "hold": slot["id"],
                "capacity": 1,
                "cost": {"minutes": 60, "money": cents // 100, "effort": "low"},
                "valid_until": VALID_UNTIL,
                "ext": {"delivery": slot["window"], "basket": euro(cents), "simulated": True},
                "needs_person": cents >= SPEND_LIMIT_CENTS,
            }
        )
    return result


def hold(slot_id: str, need_id: str, held: dict[str, str]) -> dict[str, Any]:
    """Hold one slot for one need. Asking again for the same need returns the same hold."""
    slot = next((s for s in SLOTS if s["id"] == slot_id), None)
    if slot is None:
        return {"ok": False, "reason": "unknown slot"}
    owner = held.get(slot_id)
    if owner is not None and owner != need_id:
        return {"ok": False, "reason": "slot already held"}
    held[slot_id] = need_id
    return {"ok": True, "id": slot_id, "need": need_id, "window": slot["window"], "state": "held"}


def order_summary(slot_id: str) -> dict[str, Any]:
    """The fixed order the grocer delivers, as a list a person can check at the door."""
    slot = next(s for s in SLOTS if s["id"] == slot_id)
    total = basket_cents() + int(slot["fee"])
    lines = [f"{item}, {amount}: {euro(price)}" for item, amount, price in BASKET]
    lines.append(f"Delivery {slot['window']}: {euro(int(slot['fee']))}")
    return {
        "title": f"Grocery delivery {slot['window']} (simulated grocer)",
        "items": lines,
        "total": euro(total),
        "note": "A simulated shop: nothing was bought and nothing will be delivered.",
    }


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
        print("usage: grocer.py <invitation-link>", file=sys.stderr)
        return 2
    base = "https://grocer.example.invalid"
    card = build_card(base, os.urandom(32))
    joined = redeem(argv[1], card, base + "/card")
    # The needs the host showed are public task data; here the grocer answers the shopping need.
    needs = [{"id": "shopping", "title": "Menu and shopping list for six", "kind": "list"}]
    print(json.dumps({"joined": joined.get("participant"), "offers": offers_for(needs)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
