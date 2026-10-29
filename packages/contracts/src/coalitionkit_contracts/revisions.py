# SPDX-License-Identifier: Apache-2.0
"""Subject revisions: the host assigns them, a decision must match the current one."""

from __future__ import annotations


class StaleSubjectError(ValueError):
    """The decision names a revision that is not the subject's current one (``stale_subject``)."""

    def __init__(self, decided: int, current: int) -> None:
        super().__init__(f"decision covers revision {decided}, current is {current}")
        self.decided = decided
        self.current = current


def first_revision() -> int:
    """A new object starts at revision 1."""
    return 1


def next_revision(current: int) -> int:
    """The revision after any change to an object."""
    if current < 1:
        raise ValueError("revisions start at 1")
    return current + 1


def is_current(decided_revision: int, current_revision: int) -> bool:
    return decided_revision == current_revision


def check_revision(decided_revision: int, current_revision: int) -> None:
    """Compare as the host does inside the recording transaction. Older or newer both fail."""
    if decided_revision != current_revision:
        raise StaleSubjectError(decided_revision, current_revision)


def is_superseded(request_revision: int, current_revision: int) -> bool:
    """A pending consent request for an older revision is superseded by a change."""
    return request_revision < current_revision
