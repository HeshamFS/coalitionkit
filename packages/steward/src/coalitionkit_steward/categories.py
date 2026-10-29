# SPDX-License-Identifier: Apache-2.0
"""Named text categories the deterministic policies can test for.

These are plain keyword patterns: cheap and predictable, with the model audit as the second
look. They are deliberately narrow so a false positive costs an escalation, not a block.
"""

from __future__ import annotations

import re

_FLAGS = re.IGNORECASE

CATEGORIES: dict[str, tuple[re.Pattern[str], ...]] = {
    "medical_dosage": (
        re.compile(r"\b\d+(?:\.\d+)?\s?(?:mg|mcg|ml|iu)\b", _FLAGS),
        re.compile(r"\b(?:take|inject|administer)\s+\d+\s+(?:tablets?|pills?|capsules?)\b", _FLAGS),
    ),
    "legal_advice": (
        re.compile(
            r"\b(?:you\s+(?:should|must)\s+(?:sue|file\s+a\s+lawsuit|plead\s+guilty)"
            r"|this\s+is\s+legal\s+advice)\b",
            _FLAGS,
        ),
    ),
    "investment_advice": (
        re.compile(
            r"\b(?:buy|sell|short)\s+(?:the\s+)?(?:shares|stocks?|crypto|bitcoin)\b", _FLAGS
        ),
        re.compile(r"\bguaranteed\s+returns?\b", _FLAGS),
    ),
}
