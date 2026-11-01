// SPDX-License-Identifier: Apache-2.0
// The only place a consent answer is built. It draws a request the host listed, from the host's
// own data (the OpenRequest and the viewer's projection), never from a composed tree.
import { useState } from "react";
import type { ConsentAcknowledgement } from "./components/f08/ConsentSeal";
import { Banner } from "./components/feedback";
import { TensionCard } from "./components/plans";
import { Card } from "./components/primitives";
import { type Answer, answerFor } from "./feed/actions";
import type { OpenRequest } from "./feed/agent";
import type { ViewerState } from "./feed/delta";
import { tensionView } from "./feed/derive";
import { ConsentSheet } from "./room/consentSheet";

export function TrustedRequest({
  request,
  state,
  onAnswer,
  onSeePlans,
}: {
  request: OpenRequest;
  state: ViewerState | null;
  onAnswer:
    | ((answer: Answer) => void)
    | ((answer: Answer) => Promise<ConsentAcknowledgement | undefined>);
  onSeePlans?: () => void;
}) {
  const [declined, setDeclined] = useState<string>();
  const [problem, setProblem] = useState<string | null>(null);
  const send = (consent: boolean, choice?: string) => {
    try {
      onAnswer(answerFor(request, consent, choice));
      setProblem(null);
    } catch (error) {
      setProblem(error instanceof Error ? error.message : "could not build the answer");
    }
  };

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
      <ConsentSheet
        request={request}
        state={state}
        declined={declined === request.id}
        onApprove={() => onAnswer(answerFor(request, true))}
        onDecline={async () => {
          // Locked only while the veto is in flight: if it fails, it can be sent again.
          setDeclined(request.id);
          try {
            await onAnswer(answerFor(request, false));
            setProblem(null);
          } catch (error) {
            setProblem(error instanceof Error ? error.message : "could not send the answer");
          } finally {
            setDeclined(undefined);
          }
        }}
        onSeePlans={onSeePlans}
      />
    </>
  );
}
