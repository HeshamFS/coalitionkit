// SPDX-License-Identifier: Apache-2.0
// The consent seal as the Consent board draws it: the question in one line, what a
// yes does, what stays private, then press and hold to say yes, which the host signs for you. Built only from
// the host's open request and the viewer's own projection, never from a composed tree.
import type { ConsentAcknowledgement } from "../components/f08/ConsentSeal";
import { TrustedConsentSeal } from "../components/f08/ConsentSeal";
import type { OpenRequest } from "../feed/agent";
import type { ViewerState } from "../feed/delta";
import { commitmentTask, derivePlans, deriveRoom } from "../feed/derive";
import "./consent.css";

type Sheet = { question: string; yes: string[]; privateNote: string };

/** Words for each kind of request. Everything quoted comes from the viewer's projection. */
export function sheetFor(request: OpenRequest, state: ViewerState | null): Sheet {
  const goal = deriveRoom(state).title;
  const privateNote =
    "Your reasons, limits and free time stay in your vault. Others learn only what you agree to.";
  if (request.kind === "charter") {
    return {
      question: "Take part in this coalition?",
      yes: [
        `You accept the goal: ${goal}`,
        "Your agent may offer and answer for you; anything that commits you asks you again",
        "The others see that you joined, by your seat",
      ],
      privateNote,
    };
  }
  if (request.kind === "plan") {
    const plan = derivePlans(state).find((p) => p.id === request.subjectId);
    return {
      question: plan ? `Choose plan ${plan.label}?` : "Choose this plan?",
      yes: [
        plan ? `Plan ${plan.label} is chosen for you` : "This plan is chosen for you",
        "Your part in it is committed only after the people it names say yes",
      ],
      privateNote,
    };
  }
  if (request.kind === "commitment") {
    const part =
      commitmentTask(state, request.subjectId)?.description || "your part in the chosen plan";
    return {
      question: "Commit to your part?",
      yes: [`You commit to: ${part}`, "The people working with you see that you committed"],
      privateNote,
    };
  }
  return { question: request.message, yes: [request.message], privateNote };
}

export function ConsentSheet({
  request,
  state,
  onApprove,
  onDecline,
  onSeePlans,
  declined,
  summary,
  compact = false,
}: {
  request: OpenRequest;
  state: ViewerState | null;
  onApprove: (() => void) | (() => Promise<ConsentAcknowledgement | undefined>);
  onDecline: () => void | Promise<void>;
  onSeePlans?: () => void;
  declined: boolean;
  /** The host's plain words for this ask. They replace the question when given. */
  summary?: string;
  /** The Table's tighter sheet: the hold button stays on the first screen. */
  compact?: boolean;
}) {
  const sheet = sheetFor(request, state);
  return (
    <section
      className="ck-consent"
      data-compact={compact}
      aria-label={`Your yes is needed: ${summary ?? sheet.question}`}
    >
      {!compact && <span className="ck-consent-eyebrow">Your agent needs your yes</span>}
      <h2 className="ck-consent-q">{summary ?? sheet.question}</h2>
      <div className="ck-consent-box">
        <span className="ck-consent-k">If you say yes</span>
        <ul className="ck-consent-yes">
          {sheet.yes.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
        <span className="ck-consent-k">What stays private</span>
        <p className="ck-consent-p">{sheet.privateNote}</p>
        {!compact && (
          <>
            <span className="ck-consent-k">What you sign</span>
            <p className="ck-consent-p ck-consent-sign">
              {request.message} · {request.kind} · revision {request.revision}
            </p>
          </>
        )}
      </div>
      <div className="ck-consent-seal">
        <TrustedConsentSeal
          key={`${request.id}:${request.revision}`}
          deadline={request.expiresAt}
          onApprove={onApprove}
        />
      </div>
      <div className="ck-consent-actions">
        <button type="button" className="btn" disabled={declined} onClick={onDecline}>
          Not this one
        </button>
        {onSeePlans && request.kind === "plan" && (
          <button type="button" className="btn" onClick={onSeePlans}>
            See the other plans
          </button>
        )}
      </div>
    </section>
  );
}
