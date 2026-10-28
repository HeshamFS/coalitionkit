# SPDX-License-Identifier: Apache-2.0
"""Private-note canaries and recursive JSON/byte scanning."""

import json
import secrets
from dataclasses import dataclass

from .store import Vault


@dataclass(frozen=True)
class Canaries:
    values: tuple[str, ...]

    @classmethod
    def plant(cls, vault: Vault, count: int) -> Canaries:
        if type(count) is not int or count < 0:
            raise ValueError("invalid canary count")
        values = tuple("canary-" + secrets.token_hex(24) for _ in range(count))
        for value in values:
            vault.add_private_note(value)
        return cls(values)

    def scan(self, value: object) -> tuple[str, ...]:
        if isinstance(value, bytes):
            text = value.decode("utf-8", errors="replace")
        elif isinstance(value, str):
            text = value
        else:
            text = json.dumps(value, ensure_ascii=False)
        try:
            decoded: object = json.loads(text)
        except ValueError, TypeError:
            decoded = None
        if decoded is not None:
            text += json.dumps(decoded, ensure_ascii=False)
        return tuple(canary for canary in self.values if canary in text)
