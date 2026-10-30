// SPDX-License-Identifier: Apache-2.0
import { Action, obj, type Props, type Send, text } from "../f08/shared";
import "../../styles/f09.css";

const messages: Record<string, [string, string]> = {
  deadline_exceeded: ["Too late to decide.", "warn"],
  stale_subject: ["That changed first.", "warn"],
  not_a_decider: ["Not yours to decide.", "bad"],
  bad_signature: ["Signature didn't check.", "bad"],
  rate_limited: ["Slow down a moment.", "info"],
  steward_blocked: ["The steward stopped this.", "bad"],
};
export function ErrorNotice({ p, send }: { p: Props; send: Send }) {
  const [title, tone] = messages[text(p.code)] ?? ["This action could not finish.", "bad"];
  return (
    <div className={`banner bn-${tone} f09-error`} role="alert">
      <div className="grow">
        <b>{title}</b> {text(obj(p.detail).message ?? obj(p.detail).reason)}{" "}
        <span className="mono st">{text(p.code)}</span>
      </div>
      {obj(p.detail).retry === true && (
        <Action label="Retry" event="error.retry" send={send} data={{ ref: p.ref, code: p.code }} />
      )}
    </div>
  );
}
