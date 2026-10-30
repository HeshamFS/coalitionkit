// SPDX-License-Identifier: Apache-2.0
import { useEffect, useRef, useState } from "react";
import { Action, expired, Frame, number, Subject, text, type View } from "../f02/ui";
import "../../styles/f02.css";
import "../../styles/f04.css";

export { AcceptanceForm } from "./acceptance";
export { AvailabilityGrid } from "./availability";
export { Form } from "./form";
export { NeedForm } from "./need";
export { OfferForm } from "./offer";
export { DocumentShare, LimitField } from "./private-input";
export { ValidationSummary } from "./validation";
export { Wizard } from "./wizard";
export function ConsentSeal({ p, send }: View) {
  const [holding, set] = useState(false);
  const [review, confirm] = useState(false);
  const [elapsed, tick] = useState(0);
  const [summary, ...description] = text(p.summary).split("\n");
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => {
    if (!holding) return;
    const started = Date.now();
    const interval = setInterval(() => tick(Date.now() - started), 100);
    return () => clearInterval(interval);
  }, [holding]);
  useEffect(() => () => clearTimeout(timer.current), []);
  const cancel = () => {
    clearTimeout(timer.current);
    timer.current = undefined;
    set(false);
  };
  const start = () => {
    if (timer.current || expired(p.decision_deadline)) return;
    tick(0);
    set(true);
    timer.current = setTimeout(
      () => {
        set(false);
        confirm(true);
        timer.current = undefined;
      },
      Math.max(0, number(p.holdMs, 1200)),
    );
  };
  return (
    <Frame name="ConsentSeal" state={holding ? "holding" : "idle"}>
      <span className="f04-seal-eyebrow">You're committing to</span>
      <b className="f04-seal-title">{summary}</b>
      {!!description.length && (
        <span className="f04-seal-description">{description.join(" ")}</span>
      )}
      <span className="f04-seal-subject">
        <Subject value={p.subject} />
      </span>
      <button
        type="button"
        className="ck-seal"
        aria-label="Hold to review consent"
        disabled={expired(p.decision_deadline)}
        onPointerDown={start}
        onPointerUp={cancel}
        onPointerLeave={cancel}
        onPointerCancel={cancel}
        onKeyDown={(e) => {
          if (e.key === " " && !e.repeat) {
            e.preventDefault();
            start();
          }
          if (e.key === "Enter") confirm(true);
        }}
        onKeyUp={(e) => {
          if (e.key === " ") cancel();
        }}
        onBlur={cancel}
      >
        <svg aria-hidden="true" viewBox="0 0 112 112">
          <circle className="f04-seal-track" cx="56" cy="56" r="48" />
          {holding && (
            <circle
              className="f04-seal-progress"
              cx="56"
              cy="56"
              r="48"
              transform="rotate(-90 56 56)"
            />
          )}
          <path d="M42 56l10 10 18-20" />
        </svg>
      </button>
      <b className="f04-seal-label">
        {holding ? `Keep holding · ${(elapsed / 1000).toFixed(1)} s` : "Hold to review"}
      </b>
      <span className="f04-seal-footnote">signs with your owner key · release to cancel</span>
      {review && (
        <fieldset aria-label="Confirm consent">
          <p>Review this revision with your owner key.</p>
          <Action
            primary
            disabled={expired(p.decision_deadline)}
            onClick={() => {
              if (!expired(p.decision_deadline)) send("decide", { subject: p.subject });
              confirm(false);
            }}
          >
            Confirm
          </Action>
          <Action onClick={() => confirm(false)}>Cancel</Action>
        </fieldset>
      )}
    </Frame>
  );
}
export { FeedbackForm } from "./feedback";
export { Receipt } from "./receipt";
export { OwnerSign, ReviewStep } from "./review";
