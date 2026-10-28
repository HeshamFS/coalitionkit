# SPDX-License-Identifier: Apache-2.0
"""What a recipient gets for a logged event: the original, a projection or only a receipt."""

from __future__ import annotations

from typing import Literal

Form = Literal["original", "projection", "receipt_only"]


def delivery_form(*, in_scope: bool, redacted: bool, viewer_specific: bool) -> Form:
    """The form of an event for one recipient, also used for the sender's acknowledgement.

    A recipient outside the event's scope gets nothing but the receipt. Inside the scope, an
    event with a field redacted for the recipient, or one that is viewer-specific, is a
    projection; any other event is delivered as the original.
    """
    if not in_scope:
        return "receipt_only"
    return "projection" if redacted or viewer_specific else "original"
