# SPDX-License-Identifier: Apache-2.0
"""Durable card pins and organizer invitations."""

from dataclasses import dataclass

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .store import EventStore


@dataclass(frozen=True)
class PinnedCard:
    key: Ed25519PublicKey
    kid: str
    participant: str


class IdentityRegistry:
    def __init__(self, store: EventStore, coalition_id: str) -> None:
        self.store, self.coalition_id = store, coalition_id
        with store.transaction(coalition_id) as tx:
            rows = tx.execute(
                "SELECT card_url, public_key, kid, participant FROM pinned_cards "
                "WHERE coalition_id = ?",
                (coalition_id,),
            ).fetchall()
            self.cards = {
                url: PinnedCard(Ed25519PublicKey.from_public_bytes(bytes.fromhex(key)), kid, owner)
                for url, key, kid, owner in rows
            }
            self.invitations = dict(
                tx.execute(
                    "SELECT participant, card_url FROM invitations WHERE coalition_id = ?",
                    (coalition_id,),
                ).fetchall()
            )

    def pin(self, url: str, participant: str, key: Ed25519PublicKey, kid: str) -> None:
        values = (key.public_bytes_raw().hex(), kid, participant)
        with self.store.transaction(self.coalition_id) as tx:
            tx.execute(
                "INSERT INTO pinned_cards VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
                (self.coalition_id, url, *values),
            )
            row = tx.execute(
                "SELECT public_key, kid, participant FROM pinned_cards "
                "WHERE coalition_id = ? AND card_url = ?",
                (self.coalition_id, url),
            ).fetchone()
            if tuple(row) != values:
                raise ValueError("pinned card cannot be replaced")
        self.cards[url] = PinnedCard(key, kid, participant)

    def invite(self, participant: str, url: str) -> None:
        with self.store.transaction(self.coalition_id) as tx:
            tx.execute(
                "INSERT INTO invitations VALUES (?, ?, ?) ON CONFLICT (coalition_id, participant) "
                "DO UPDATE SET card_url = excluded.card_url",
                (self.coalition_id, participant, url),
            )
        self.invitations[participant] = url
