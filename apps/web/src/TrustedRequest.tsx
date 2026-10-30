// SPDX-License-Identifier: Apache-2.0
// The only place a consent answer is built. It draws a request the host listed, from the host's
// own data (the OpenRequest and the viewer's projection), never from a composed tree.
import { useState } from "react";
import { ConsentCard } from "./components/consent";
import { type ConsentAcknowledgement, TrustedConsentSeal } from "./components/f08/ConsentSeal";
import { Banner } from "./components/feedback";
import { TensionCard } from "./components/plans";
import { Card } from "./components/primitives";
import { type Answer, answerFor } from "./feed/actions";
import type { OpenRequest } from "./feed/agent";
import type { ViewerState } from "./feed/delta";
import { tensionView } from "./feed/derive";
import { usePhoneRoom } from "./room/media";

export function TrustedRequest({
  request,
  state,
  onAnswer,
}: {
  request: OpenRequest;
  state: ViewerState | null;
  onAnswer:
    | ((answer: Answer) => void)
    | ((answer: Answer) => Promise<ConsentAcknowledgement | undefined>);
}) {
  const phone = usePhoneRoom();
  const [phoneSent, setPhoneSent] = useState<string>();
  const [problem, setProblem] = useState<string | null>(null);
  const send = (consent: boolean, choice?: string) => {
    try {
      onAnswer(answerFor(request, consent, choice));
      setProblem(null);
    } catch (error) {
      setProblem(error instanceof Error ? error.message : "could not build the answer");
    }
  };
  const subject = { kind: request.kind, id: request.subjectId, revision: request.revision };

  if (request.kind === "tension_option") {
    const view = tensionView(state, request.subjectId, request.revision);
    if (!view) {
      return (
        <Card tone="ask" title="Choice to decide">
          <span className="small">{request.message}</span>
          <span className="small">Options unavailable.</span>
        </Card>
      );
    }
    return (
      <>
        {problem && <Banner tone="blocked" title="Could not send." body={problem} />}
        <TensionCard
          title={request.message}
          options={view.options.map((o) => ({ ...o, tradeoffs: [] }))}
          deadline={request.expiresAt}
          onChoose={(option) => send(true, option)}
        />
        {view.tradeoffs.length > 0 && (
          <ul className="small" aria-label="Trade-offs">
            {view.tradeoffs.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
        )}
      </>
    );
  }
  if (phone)
    return (
      <section
        className="trusted-phone-consent"
        aria-label={`Consent to decide: ${request.message}`}
      >
        <span className="small">Your agent needs your yes</span>
        <h2>{request.message}</h2>
        <span className="small">
          {request.subjectId} · revision {request.revision}
        </span>
        <TrustedConsentSeal
          key={`${request.id}:${request.revision}`}
          deadline={request.expiresAt}
          onApprove={() => {
            const answer = answerFor(request, true);
            setPhoneSent(request.id);
            return onAnswer(answer);
          }}
        />
        <button
          type="button"
          className="btn"
          disabled={phoneSent === request.id}
          onClick={() => send(false)}
        >
          Not this one
        </button>
        {problem && <Banner tone="blocked" title="Could not send." body={problem} />}
      </section>
    );
  return (
    <>
      {problem && <Banner tone="blocked" title="Could not send." body={problem} />}
      <ConsentCard
        subject={subject}
        title={request.message}
        deadline={request.expiresAt}
        onDecide={(consent) => send(consent)}
      />
    </>
  );
}
