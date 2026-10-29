# SPDX-License-Identifier: Apache-2.0
"""Ports the surfaces depend on. Real adapters live outside the core; fakes are in ``fakes``."""

from __future__ import annotations

from typing import Any, Protocol

Document = dict[str, Any]


class OwnerSigner(Protocol):
    """Turns a person's yes or no into a signed ``coalition.decide`` envelope.

    ``subject`` is ``{kind, id, revision}``. ``choice`` is the value the decision names (the
    subject id for every kind except ``tension_option``). The returned envelope must be signed
    by the agent key and carry a ``consent_sig`` made with the OWNER key. The surface verifies
    that before it sends anything.
    """

    def sign_decision(self, subject: Document, choice: str, consent: bool) -> Document: ...


class ViewerAuth(Protocol):
    """Maps a bearer token to the participant it speaks for, or ``None``."""

    def viewer_for(self, token: str) -> str | None: ...
