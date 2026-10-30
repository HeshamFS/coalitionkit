// SPDX-License-Identifier: Apache-2.0
import { expired, Frame, list, number, obj, text, type View } from "../f02/ui";
import "./details.css";

export function OwnerSign({ p, send }: View) {
  const subject = obj(p.subject);
  return (
    <Frame name="OwnerSign" state={p.kid ? "ready" : "failed closed"}>
      <div className="row">
        <svg className="ico blue" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="8" cy="15" r="4" />
          <path d="M11 12l9-9M17 6l3 3M15 8l2 2" />
        </svg>
        <b>Sign as yourself</b>
      </div>
      <span className="small">
        This decision is binding. Your device signs it; the agent can't.
      </span>
      <dl>
        <dt>Subject</dt>
        <dd>
          {text(p.subject_label) || `${text(subject.kind)} ${text(subject.id)}`} · rev{" "}
          {number(subject.revision)}
        </dd>
        <dt>Answer</dt>
        <dd>
          <b>{text(p.answer_label) || text(p.answer)}</b>
        </dd>
        <dt>Key</dt>
        <dd className="mono">{text(p.kid) || "No key available"}</dd>
        <dt>Device</dt>
        <dd>
          {p.device_label ? `${text(p.device_label)} · ` : ""}
          {text(p.method)}
        </dd>
      </dl>
      <button
        type="button"
        className="btn btn-ink"
        disabled={!p.kid || expired(p.decision_deadline)}
        onClick={() =>
          send("sign.confirm", {
            subject: p.subject,
            answer: p.answer,
            kid: p.kid,
            method: p.method,
          })
        }
      >
        <svg className="ico ico-sm" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 11c0 3-1 6-3 8M8 6a6 6 0 0 1 10 4c0 4-1 7-2 9M5 10a7 7 0 0 1 1-3M12 15c0 2-.5 3.5-1.5 5" />
        </svg>
        Confirm with {text(p.method) || "owner key"}
      </button>
      <span className="st">fails closed: no key, no decision</span>
    </Frame>
  );
}

export function ReviewStep({ p, send }: View) {
  const passed = obj(p.precheck).passed === true;
  return (
    <Frame name="ReviewStep" state={passed ? "ready" : "blocked"}>
      <div className="f04-review-grid">
        <div className="f04-review-sections">
          {list(p.sections).map((section, i) => (
            <div className="row sp card" key={String(i)}>
              <div className="col">
                <span className="st">{text(section.label)}</span>
                <span className="small">{text(section.summary)}</span>
              </div>
              <button
                className="f04-text-button small"
                type="button"
                onClick={() => send("wizard.edit", { step: section.editStep })}
              >
                Edit
              </button>
            </div>
          ))}
        </div>
        <div className="col">
          <div className="banner bn-info">
            <svg className="ico" viewBox="0 0 24 24" aria-hidden="true">
              <circle cx="12" cy="12" r="9" />
              <path d="M12 11v5M12 8h.01" />
            </svg>
            <div>{text(p.notice)}</div>
          </div>
          <div className="row">
            <span className="small">Steward pre-check</span>
            <span className={`badge ${passed ? "b-signed" : "f04-over"}`}>
              {passed ? "Passed" : "Blocked"}
            </span>
          </div>
          <div className="row">
            <button
              type="button"
              className="btn btn-sm btn-ghost"
              onClick={() => send("wizard.back")}
            >
              Back
            </button>
            <button
              type="button"
              className="btn btn-primary f04-push"
              disabled={!passed}
              onClick={() => send("wizard.finish")}
            >
              Publish charter
            </button>
          </div>
        </div>
      </div>
    </Frame>
  );
}
