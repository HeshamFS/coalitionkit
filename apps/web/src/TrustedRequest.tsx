// SPDX-License-Identifier: Apache-2.0
// The only place a consent answer is built. It draws a request the host listed, from the host's
// own data (the OpenRequest and the viewer's projection), never from a composed tree.
import { useState } from "react";
import { ConsentCard } from "./components/consent";
import { Banner } from "./components/feedback";
import { TensionCard } from "./components/plans";
import { Card } from "./components/primitives";
import { type Answer, answerFor } from "./feed/actions";
import type { OpenRequest } from "./feed/agent";
import type { ViewerState } from "./feed/delta";
import { tensionView } from "./feed/derive";

export function TrustedRequest({
  request,
  state,
  onAnswer,
}: {
  request: OpenRequest;
  state: ViewerState | null;
  onAnswer: (answer: Answer) => void;
}) {
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
