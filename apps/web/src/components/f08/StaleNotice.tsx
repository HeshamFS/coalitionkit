// SPDX-License-Identifier: Apache-2.0
import { Action, list, type Props, type Send, text } from "./shared";
import "../../styles/f08.css";

export function StaleNotice({ p, send }: { p: Props; send: Send }) {
  return (
    <>
      <div className="banner bn-warn">
        Changed to revision {text(p.currentRevision)} while you were reading. Your answer was not
        sent.
      </div>
      {list(p.diff).map((v) => (
        <span className="mono small" key={text(v)}>
          {text(v)}
        </span>
      ))}
      <Action
        label={`Review revision ${text(p.currentRevision)}`}
        event="subject.review"
        send={send}
        data={{ subject: p.subject }}
        primary
      />
    </>
  );
}
