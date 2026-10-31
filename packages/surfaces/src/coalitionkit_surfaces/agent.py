# SPDX-License-Identifier: Apache-2.0
"""The agent session: messages to one person and their consent requests as interrupts."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

from ag_ui.core import (
    Interrupt,
    RunErrorEvent,
    RunFinishedEvent,
    RunFinishedInterruptOutcome,
    RunFinishedSuccessOutcome,
    RunStartedEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
)

from coalitionkit_contracts import SignatureError, jwk_to_public_key, new_ulid, verify_consent
from coalitionkit_runtime import AuthenticatedSender, CoalitionHost

from .frames import Document, Frame, KeepAlive
from .ports import OwnerSigner

KEEP_ALIVE_SECONDS = 15.0
REASON = "consent_required"
RESPONSE_SCHEMA: Document = {
    "type": "object",
    "properties": {"consent": {"type": "boolean"}, "choice": {"type": "string"}},
    "required": ["consent"],
}


class ConsentError(Exception):
    """A consent answer was refused. ``code`` is stable; ``detail`` is safe to show."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code, self.detail = code, detail


@dataclass(frozen=True)
class ConsentRequest:
    kind: str
    subject_id: str
    revision: int
    decider: str

    @property
    def interrupt_id(self) -> str:
        return f"{self.kind}:{self.subject_id}:{self.revision}:{self.decider}"

    @property
    def subject(self) -> Document:
        return {"kind": self.kind, "id": self.subject_id, "revision": self.revision}

    @classmethod
    def parse(cls, interrupt_id: str) -> ConsentRequest:
        parts = interrupt_id.split(":", 3)
        if len(parts) != 4 or not parts[2].isdigit():
            raise ConsentError("unknown_request")
        return cls(parts[0], parts[1], int(parts[2]), parts[3])


def open_requests(host: CoalitionHost, viewer: str) -> list[ConsentRequest]:
    """Pending consent rows of this decider on the host ledger, for the current revision only."""
    return [
        ConsentRequest(row["kind"], row["id"], row["revision"], viewer)
        for row in host.open_consents(viewer)
    ]


class AgentSession:
    """Interrupts and agent text for one viewer. Answers become owner-signed decisions."""

    def __init__(
        self,
        host: CoalitionHost,
        viewer: str,
        signer: OwnerSigner,
        *,
        clock: Callable[[], float],
        new_id: Callable[[], str] = new_ulid,
        outbox: deque[str] | None = None,
        keep_alive: float = KEEP_ALIVE_SECONDS,
        on_refusal: Callable[[str, str, Document], None] | None = None,
    ) -> None:
        self.host, self.viewer, self.signer = host, viewer, signer
        self.clock, self.new_id, self.keep_alive = clock, new_id, keep_alive
        self.outbox: deque[str] = outbox if outbox is not None else deque()
        self.thread_id = f"{host.coalition_id}:{viewer}:agent"
        self._shown: frozenset[str] = frozenset()
        self._last_sent = 0.0
        self._closed = False
        self.on_refusal = on_refusal

    def say(self, text: str) -> None:
        """Queue a message from an agent to this person (the caller addresses it to them)."""
        self.outbox.append(text)

    # -- frames ------------------------------------------------------------------------------

    def start(self) -> list[Frame]:
        return self._run()

    def changed(self) -> list[Frame]:
        """Call after a bus wake: a new run only when the set of open requests changed."""
        if self._closed:
            return []
        ids = frozenset(r.interrupt_id for r in open_requests(self.host, self.viewer))
        return self._run() if ids != self._shown else []

    def tick(self) -> list[Frame]:
        if self._closed:
            return []
        if self.outbox:
            return self._run()
        if self.clock() - self._last_sent >= self.keep_alive:
            self._last_sent = self.clock()
            return [KeepAlive()]
        return []

    def fail(self, message: str, code: str | None = None) -> list[Frame]:
        self._closed = True
        return [RunErrorEvent(message=message, code=code)]

    def _run(self) -> list[Frame]:
        run_id = self.new_id()
        frames: list[Frame] = [RunStartedEvent(thread_id=self.thread_id, run_id=run_id)]
        while self.outbox:
            message_id = self.new_id()
            frames += [
                TextMessageStartEvent(message_id=message_id, role="assistant"),
                TextMessageContentEvent(message_id=message_id, delta=self.outbox.popleft()),
                TextMessageEndEvent(message_id=message_id),
            ]
        requests = open_requests(self.host, self.viewer)
        self._shown = frozenset(r.interrupt_id for r in requests)
        outcome = (
            RunFinishedInterruptOutcome(interrupts=[self._interrupt(r) for r in requests])
            if requests
            else RunFinishedSuccessOutcome()
        )
        frames.append(RunFinishedEvent(thread_id=self.thread_id, run_id=run_id, outcome=outcome))
        self._last_sent = self.clock()
        return frames

    def _interrupt(self, request: ConsentRequest) -> Interrupt:
        # Only the subject goes out: nothing else about it is known to be in this viewer's scope.
        deadline = self.host.state.subject(request.kind, request.subject_id).get(
            "decision_deadline"
        )
        return Interrupt(
            id=request.interrupt_id,
            reason=REASON,
            message=f"Your decision is needed on a {request.kind.replace('_', ' ')}",
            response_schema=RESPONSE_SCHEMA,
            expires_at=deadline if isinstance(deadline, str) else None,
            metadata={"subject": request.subject},
        )

    # -- answers -----------------------------------------------------------------------------

    def answer(self, interrupt_id: str, consent: bool, choice: str | None = None) -> Document:
        """Turn this person's answer into an owner-signed ``coalition.decide`` and send it."""
        request = ConsentRequest.parse(interrupt_id)
        if request.decider != self.viewer:
            raise ConsentError("not_your_request")
        if request not in open_requests(self.host, self.viewer):
            raise ConsentError("not_open", "answered, superseded or never asked")
        if request.kind == "tension_option":
            if not choice:
                raise ConsentError("choice_required", "name the option")
        elif choice not in (None, request.subject_id):
            raise ConsentError("bad_choice", "choice must equal the subject id")
        chosen = choice or request.subject_id
        envelope = self.signer.sign_decision(request.subject, chosen, consent)
        member = self.host.state.members[self.viewer]
        self._verify(envelope, request, chosen, consent, member["owner_key"])
        result = self.host.accept(envelope, AuthenticatedSender(member["sender"], self.viewer))
        if isinstance(result, dict):
            if self.on_refusal is not None:
                self.on_refusal(self.viewer, "coalition.decide", result["payload"])
            raise ConsentError(result["payload"]["code"], "the host refused the decision")
        accepted = result.accepted
        assert accepted is not None
        # The owner's signature is part of the decide event every decider receives; returning it
        # lets the trusted card show the receipt the person just signed.
        return {
            "status": "accepted",
            "seq": accepted["seq"],
            "consent_sig": envelope["payload"]["consent_sig"],
        }

    def _verify(
        self, envelope: Document, request: ConsentRequest, choice: str, consent: bool, jwk: Document
    ) -> None:
        body = envelope.get("payload", {})
        exact = (
            envelope.get("type") == "coalition.decide"
            and envelope.get("coalition_id") == self.host.coalition_id
            and envelope.get("on_behalf_of") == self.viewer
            and body.get("subject") == request.subject
            and body.get("choice") == choice
            and body.get("consent") is consent
        )
        if not exact:
            raise ConsentError("signer_mismatch", "the signed decision is not the person's answer")
        try:
            verify_consent(
                self.host.coalition_id,
                body,
                jwk_to_public_key(jwk),
                participant=self.viewer,
                expected_kid=jwk["kid"],
            )
        except SignatureError:
            raise ConsentError("bad_signature", "not signed by the owner key") from None
