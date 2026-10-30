// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { ConsentCard as Consent } from "./legacy";
import { num, obj, type Props, type Send, text, usePreviewState } from "./shared";
import "../../styles/f08.css";

export function Disclosure({ p, send }: { p: Props; send: Send }) {
  const levels = ["none", "bool", "range", "exact"];
  return (
    <>
      <div className="f08-ladder">
        {levels.map((level, i) => (
          <button
            type="button"
            className={`card ${p.level === level ? "card-live" : ""}`}
            key={level}
            aria-pressed={p.level === level}
            onClick={() =>
              send(i > levels.indexOf(text(p.level)) ? "disclosure.raise" : "disclosure.lower", {
                field: p.field,
                level,
              })
            }
          >
            <span className="eyebrow">
              {i + 1} · {["nothing", "yes / no", "a range", "exact"][i]}
            </span>
            <span className="small">
              {["Agents can't ask", "Answer only", text(p.buckets), "Asks you every time"][i]}
            </span>
          </button>
        ))}
      </div>
      <span className="small">Each step up shows who would learn it and asks first</span>
    </>
  );
}
export function Approval({ p, send }: { p: Props; send: Send }) {
  const preview = usePreviewState();
  const [signing, setSigning] = useState(preview === "signing");
  const expired = Date.parse(text(p.decision_deadline)) <= Date.now();
  return (
    <>
      <button
        type="button"
        className="btn btn-primary btn-lg"
        disabled={Boolean(p.disabledReason) || signing || expired}
        aria-busy={signing}
        onClick={() => {
          setSigning(true);
          send("approve", {
            subject: p.subject,
            consequence: p.consequence,
            decision_deadline: p.decision_deadline,
          });
        }}
      >
        {signing ? "Signing…" : text(p.label)}
      </button>
      <span className="small">{text(p.consequence)}</span>
      <span className="st">{expired ? "Deadline passed" : text(p.disabledReason)}</span>
    </>
  );
}
export function ConsentView({ p, send }: { p: Props; send: Send }) {
  const preview = usePreviewState();
  const subject = obj(p.subject);
  const expired = Date.parse(text(p.decision_deadline)) <= Date.now();
  return (
    <>
      <Consent
        subject={{
          kind: text(subject.kind),
          id: text(subject.id),
          revision: num(subject.revision),
        }}
        title={text(p.summary)}
        yourPart={text(p.yourPart)}
        cost={text(p.cost)}
        consequenceOfNo={text(p.consequenceOfNo)}
        deadline={text(p.decision_deadline)}
        state={
          expired ? "expired" : preview === "answered" || preview === "stale" ? preview : "open"
        }
        answer={preview === "answered"}
        currentRevision={preview === "stale" ? num(subject.revision) + 1 : undefined}
        onReview={() => send("compare", { subject: p.subject })}
        onDecide={(consent) =>
          send("decide", {
            subject: p.subject,
            consent,
            consequence: p.consequence,
            decision_deadline: p.decision_deadline,
          })
        }
        onCompare={() => send("compare", { subject: p.subject })}
      />
      <span className="small">{text(p.consequence)}</span>
    </>
  );
}
