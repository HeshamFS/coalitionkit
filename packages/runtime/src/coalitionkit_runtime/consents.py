# SPDX-License-Identifier: Apache-2.0
"""Durable requests with conditional first-answer-wins updates."""

from __future__ import annotations

import json
from collections.abc import Sequence

from coalitionkit_contracts import check_revision, tally
from coalitionkit_contracts.decisions import State

from .store import Document, Transaction


class ConsentLedger:
    def __init__(self, tx: Transaction, coalition_id: str) -> None:
        self.tx = tx
        self.coalition_id = coalition_id

    def request(self, subject: Document, deciders: Sequence[str]) -> None:
        key = (self.coalition_id, subject["kind"], subject["id"])
        self.tx.execute(
            "UPDATE consents SET status = 'superseded' WHERE coalition_id = ? "
            "AND kind = ? AND subject_id = ? AND revision < ? AND status = 'pending'",
            (*key, subject["revision"]),
        )
        for decider in deciders:
            self.tx.execute(
                "INSERT INTO consents VALUES (?, ?, ?, ?, ?, 'pending', NULL) "
                "ON CONFLICT DO NOTHING",
                (*key, subject["revision"], decider),
            )

    def answer(self, subject: Document, current: int, decider: str, consent: bool) -> bool:
        check_revision(subject["revision"], current)
        result = self.tx.execute(
            "UPDATE consents SET status = 'answered', answer = ? WHERE coalition_id = ? "
            "AND kind = ? AND subject_id = ? AND revision = ? AND decider = ? "
            "AND status = 'pending'",
            (
                json.dumps(consent),
                self.coalition_id,
                subject["kind"],
                subject["id"],
                current,
                decider,
            ),
        )
        return result.rowcount == 1

    def tally(self, subject: Document, deciders: Sequence[str]) -> State:
        rows = self.tx.execute(
            "SELECT decider, answer FROM consents WHERE coalition_id = ? AND kind = ? "
            "AND subject_id = ? AND revision = ? AND status = 'answered'",
            (self.coalition_id, subject["kind"], subject["id"], subject["revision"]),
        ).fetchall()
        return tally(deciders, {row[0]: json.loads(row[1]) for row in rows})
