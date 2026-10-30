// SPDX-License-Identifier: Apache-2.0
import { useContext, useState } from "react";
import { ConsentCard as Consent } from "./legacy";
import { DisclosurePreviews, PrivacyDoor } from "./presentation";
import { num, obj, type Props, type Send, text, usePreviewState } from "./shared";
import "../../styles/f08.css";

export function Disclosure({ p, send }: { p: Props; send: Send }) {
  const levels = ["none", "bool", "range", "exact"];
  const preview = useContext(DisclosurePreviews)[text(p.field)];
  return (
    <>
      <div className="f08-ladder">
        {levels.map((level, i) => (
          <button
            type="button"
            className={`card f08-level ${p.level === level ? "card-live" : ""}`}
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
            <span className="small" style={{ color: "var(--ink)" }}>
              {
                [
                  "Agents can't ask",
                  preview ? (
                    <>
                      {preview.question} → <b>{preview.answer}</b>
                    </>
                  ) : (
                    "A question within your limit → yes"
                  ),
                  text(p.buckets),
                  preview?.exact ?? "Exact value",
                ][i]
              }
            </span>
            {i === 0 ? (
              <span className="redact" style={{ width: "100%", height: 10, opacity: 0.15 }} />
            ) : (
              <span className="st">
                {i === 1
                  ? `chosen for: ${text(p.field).toLowerCase()}`
                  : i === 2
                    ? "buckets set by you"
                    : "asks you every time"}
              </span>
            )}
          </button>
        ))}
      </div>
      <div className="slider" style={{ marginTop: 4 }} aria-hidden="true">
        <div className="track" />
        <div
          className="fill"
          style={{ left: 0, width: `${12 + levels.indexOf(text(p.level)) * 25}%` }}
        />
        <div className="knob" style={{ left: `${12 + levels.indexOf(text(p.level)) * 25}%` }} />
      </div>
      <div className="row small">
        <span>{text(p.field)}</span>
        <span className="h-right">Each step up shows who would learn it and asks first</span>
      </div>
    </>
  );
}
export function Approval({ p, send }: { p: Props; send: Send }) {
  const door = useContext(PrivacyDoor);
  const preview = usePreviewState();
  const [signing, setSigning] = useState(preview === "signing");
  const expired = Date.parse(text(p.decision_deadline)) <= Date.now();
  if (door === "lens")
    return (
      <div className="f08-approval-lens" role="note">
        <span>{text(p.label)}</span>
        <span className="mono">money: confirm on your phone</span>
      </div>
    );
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
      <span className="small">
        {expired
          ? "Deadline passed"
          : p.disabledReason
            ? `Disabled: ${text(p.disabledReason)}`
            : text(p.consequence)}
      </span>
    </>
  );
}
export function ConsentView({ p, send }: { p: Props; send: Send }) {
  const preview = usePreviewState();
  const subject = obj(p.subject);
  const expired = Date.parse(text(p.decision_deadline)) <= Date.now();
  return (
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
      deadline={deadlineLabel(text(p.decision_deadline))}
      yesLabel={text(p.acceptLabel) || "Accept"}
      noLabel={subject.kind === "plan" ? "Not this plan" : "Not this one"}
      state={expired ? "expired" : preview === "answered" || preview === "stale" ? preview : "open"}
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
  );
}

function deadlineLabel(value: string) {
  const minutes = Math.max(0, Math.ceil((Date.parse(value) - Date.now()) / 60000));
  if (!Number.isFinite(minutes)) return value;
  if (minutes >= 1440)
    return new Intl.DateTimeFormat("en-GB", {
      weekday: "short",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(value));
  return `${Math.floor(minutes / 60)} h ${minutes % 60} min left`;
}
