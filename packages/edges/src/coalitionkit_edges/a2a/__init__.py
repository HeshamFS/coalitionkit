# SPDX-License-Identifier: Apache-2.0
"""The A2A edge of CoalitionKit: host server, member client and card identity."""

from .client import Ack, EdgeCallError, MemberClient, ReceivedError
from .host_port import FakeHost, HostPort, HostSigner
from .identity import (
    CardError,
    CardKey,
    CardRegistry,
    CredentialRegistry,
    OwnerBindingError,
    PinnedCard,
    card_key_entry,
    coalition_extension,
    fetch_card,
    sign_card,
    verify_card,
)
from .server import HostIdentity, build_host_card, create_host_app
from .wire import ENVELOPE_MEDIA_TYPE, EXTENSION_URI

__all__ = [
    "ENVELOPE_MEDIA_TYPE",
    "EXTENSION_URI",
    "Ack",
    "CardError",
    "CardKey",
    "CardRegistry",
    "CredentialRegistry",
    "EdgeCallError",
    "FakeHost",
    "HostIdentity",
    "HostPort",
    "HostSigner",
    "MemberClient",
    "OwnerBindingError",
    "PinnedCard",
    "ReceivedError",
    "build_host_card",
    "card_key_entry",
    "coalition_extension",
    "create_host_app",
    "fetch_card",
    "sign_card",
    "verify_card",
]
