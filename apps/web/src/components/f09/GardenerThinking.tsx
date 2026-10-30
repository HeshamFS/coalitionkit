// SPDX-License-Identifier: Apache-2.0
import { type Props, rows, type Send, text } from "../f08/shared";
import "../../styles/f09.css";
export function GardenerThinking({ p }: { p: Props; send: Send }) {
  return (
    <div className="card f09-thinking">
      <div className="row">
        <span className="av av-sq sh av-ring">{text(p.actor).slice(0, 1)}</span>
        <b>Re-planning after the change</b>
      </div>
      <div className="col f09-steps">
        {rows(p.steps).map((step, i) => (
          <div className={`row small f09-step-${text(step.state)}`} key={text(step.name) || `${i}`}>
            {step.state === "done" ? (
              <svg className="ico ico-sm" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M5 12l5 5 9-10" />
              </svg>
            ) : (
              <span className={step.state === "running" ? "spinner" : "f09-step-space"}>
                {step.state === "failed" ? "×" : ""}
              </span>
            )}
            <span className="grow">
              {step.state === "running" ? <b>{text(step.name)}</b> : text(step.name)}
            </span>
            {(step.state === "done" || step.state === "running") && (
              <span className="st">{step.state === "running" ? "…" : `${text(step.took)} s`}</span>
            )}
          </div>
        ))}
      </div>
      <span className="st">STEP_STARTED / STEP_FINISHED · no plan details until proposed</span>
    </div>
  );
}
