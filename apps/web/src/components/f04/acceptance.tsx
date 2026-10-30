// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { expired, Frame, list, number, obj, text, type View } from "../f02/ui";
import "./acceptance.css";

export function AcceptanceForm({ p, send }: View) {
  const [read, set] = useState(false);
  const subject = obj(p.subject);
  const diff = list(p.diff);
  return (
    <Frame name="AcceptanceForm" state={read ? "acknowledged" : "pending"}>
      <div className="f04-acceptance-head">
        <span className="f04-acceptance-eyebrow">
          Charter · revision {number(subject.revision)}
        </span>
        <span className="tag t-changed">Changed</span>
      </div>
      <b className="f04-acceptance-title">
        {diff.length === 1
          ? text(diff[0]?.heading) || `The ${text(diff[0]?.rule).toLowerCase()} rule changed`
          : "The charter changed"}
      </b>
      {diff.map((change, index) => (
        <div className="f04-acceptance-diff" key={text(change.rule) || String(index)}>
          <del>
            − {text(change.rule).toLowerCase()}: {text(change.before)}
          </del>
          <ins>
            + {text(change.rule).toLowerCase()}: {text(change.after)}
          </ins>
        </div>
      ))}
      <span className="f04-acceptance-consequence">{text(p.consequence)}</span>
      <label className="f04-acceptance-check">
        <input type="checkbox" checked={read} onChange={(event) => set(event.target.checked)} />
        <span>I read what changed</span>
      </label>
      <div className="f04-acceptance-actions">
        <button
          className="ck-action ck-primary"
          type="button"
          disabled={!read || expired(p.decision_deadline)}
          onClick={() => send("decide", { charter: p.charter, subject: p.subject })}
        >
          Accept revision {number(subject.revision)}
        </button>
        <button className="ck-action" type="button" onClick={() => send("leave")}>
          Leave instead
        </button>
      </div>
    </Frame>
  );
}
