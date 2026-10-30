// SPDX-License-Identifier: Apache-2.0
import { Action, list, obj, type Props, type Send, text } from "./shared";
import "../../styles/f08.css";

export function StaleNotice({ p, send }: { p: Props; send: Send }) {
  return (
    <>
      <div className="banner bn-warn">
        <svg className="ico" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 3l10 18H2z" />
          <path d="M12 10v4M12 17h.01" />
        </svg>
        <div>
          <b>
            {text(obj(p.subject).id)} changed to revision {text(p.currentRevision)}
          </b>{" "}
          while you were reading.{" "}
          {list(p.diff)
            .map((v) => text(obj(v).description))
            .filter(Boolean)
            .join(" ")}{" "}
          Your answer was not sent.
        </div>
      </div>
      <div className="f08-diff">
        {list(p.diff).map((v) => (
          <span className={text(v).startsWith("+") ? "f08-added" : "f08-removed"} key={text(v)}>
            {text(v)}
          </span>
        ))}
      </div>
      <div className="row">
        <Action
          label={`Review revision ${text(p.currentRevision)}`}
          event="subject.review"
          send={send}
          data={{ subject: p.subject }}
          primary
        />
      </div>
    </>
  );
}
