# SPDX-License-Identifier: Apache-2.0
"""Durable invitation redemption, hashed credentials and encrypted hosted keys."""

import base64
import hashlib
import json
import secrets
from threading import RLock
from urllib.parse import quote

from a2a.types import AgentCard
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from google.protobuf.json_format import MessageToDict, ParseDict

from coalitionkit_edges.a2a import CredentialRegistry
from coalitionkit_mcp import HostedParticipant
from coalitionkit_runtime import EventStore

from .adapter import Document, HostPort
from .cards import member_card


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class Registry(CredentialRegistry):
    def __init__(self, store: EventStore, key: Ed25519PrivateKey, base: str) -> None:
        super().__init__()
        self.store, self.base = store, base
        self.lock = RLock()
        self.cipher = Fernet(
            base64.urlsafe_b64encode(
                hashlib.sha256(b"coalitionkit-hosted-keys" + key.private_bytes_raw()).digest()
            )
        )
        with store.transaction("") as tx:
            tx.execute(
                "CREATE TABLE IF NOT EXISTS server_invites "
                "(digest TEXT PRIMARY KEY, coalition TEXT, participant TEXT)"
            )
            tx.execute(
                "CREATE TABLE IF NOT EXISTS server_credentials "
                "(digest TEXT PRIMARY KEY, coalition TEXT, participant TEXT, "
                "card_url TEXT, hosted TEXT, card TEXT, UNIQUE(coalition, participant))"
            )

    def issue(self, coalition: str, participant: str) -> str:
        token = secrets.token_urlsafe(32)
        with self.store.transaction(coalition) as tx:
            tx.execute(
                "INSERT INTO server_invites VALUES (?, ?, ?)",
                (digest(token), coalition, participant),
            )
        return token

    def lookup(self, token: str) -> Document | None:
        with self.store.transaction("") as tx:
            row = tx.execute(
                "SELECT coalition, participant, card_url, hosted FROM "
                "server_credentials WHERE digest = ?",
                (digest(token),),
            ).fetchone()
        return (
            dict(zip(("coalition", "participant", "card_url", "hosted"), row, strict=True))
            if row
            else None
        )

    def authenticate(self, token: str) -> str | None:
        row = self.lookup(token)
        return row["card_url"] if row else None

    async def participant_for(self, token: str) -> HostedParticipant | None:
        row = self.lookup(token)
        return self.person(row) if row and row["hosted"] else None

    def person(self, row: Document) -> HostedParticipant:
        keys = json.loads(self.cipher.decrypt(row["hosted"].encode()))
        return HostedParticipant(
            row["participant"],
            row["card_url"],
            Ed25519PrivateKey.from_private_bytes(bytes.fromhex(keys["agent"])),
            "agent",
            Ed25519PrivateKey.from_private_bytes(bytes.fromhex(keys["owner"])),
            "owner",
        )

    def hosted_for(self, coalition: str, participant: str) -> HostedParticipant:
        with self.store.transaction(coalition) as tx:
            row = tx.execute(
                "SELECT card_url, hosted FROM server_credentials "
                "WHERE coalition = ? AND participant = ?",
                (coalition, participant),
            ).fetchone()
        if not row or not row[1]:
            raise ValueError("participant has no hosted signer")
        return self.person({"participant": participant, "card_url": row[0], "hosted": row[1]})

    def redeem(
        self,
        token: str,
        ports: dict[str, HostPort],
        card_url: str | None,
        card_data: Document | None,
    ) -> Document:
        # Serializes local redemption; the unique credential row prevents cross-process reuse.
        with self.lock:
            with self.store.transaction("") as tx:
                invitation = tx.execute(
                    "SELECT coalition, participant FROM server_invites WHERE digest = ?",
                    (digest(token),),
                ).fetchone()
            if invitation is None:
                raise ValueError("invalid invitation")
            coalition, participant = invitation
            hosted = ""
            if card_url is None and card_data is None:
                agent, owner = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
                card_url = f"{self.base}/cards/{coalition}/{quote(participant, safe='')}"
                card = member_card(self.base, agent)
                hosted = self.cipher.encrypt(
                    json.dumps(
                        {
                            "agent": agent.private_bytes_raw().hex(),
                            "owner": owner.private_bytes_raw().hex(),
                        }
                    ).encode()
                ).decode()
            elif card_url and card_data:
                card = ParseDict(card_data, AgentCard())
            else:
                raise ValueError("card_url and card must be supplied together")
            port = ports[coalition]
            pin = port.cards.admit(card_url, card)
            previous = port.host.cards.get(card_url)
            if previous and (
                previous.participant != participant
                or previous.kid != pin.kid
                or previous.key.public_bytes_raw() != pin.public_key.public_bytes_raw()
            ):
                raise ValueError("card binding conflicts")
            credential = secrets.token_urlsafe(32)
            with self.store.transaction(coalition) as tx:
                tx.execute(
                    "INSERT INTO server_credentials VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        digest(credential),
                        coalition,
                        participant,
                        card_url,
                        hosted,
                        json.dumps(MessageToDict(card)),
                    ),
                )
                tx.execute("DELETE FROM server_invites WHERE digest = ?", (digest(token),))
            port.invite(participant, card_url, card)
            return {
                "coalition_id": coalition,
                "participant": participant,
                "card_url": card_url,
                "token": credential,
            }

    def restore(self, ports: dict[str, HostPort]) -> None:
        with self.store.transaction("") as tx:
            rows = tx.execute(
                "SELECT coalition, participant, card_url, card FROM server_credentials"
            ).fetchall()
        for coalition, participant, url, card in rows:
            ports[coalition].invite(participant, url, ParseDict(json.loads(card), AgentCard()))
