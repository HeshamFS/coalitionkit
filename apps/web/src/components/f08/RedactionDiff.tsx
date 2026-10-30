// SPDX-License-Identifier: Apache-2.0
import { Action, obj, type Props, type Send, text } from "./shared";
import "../../styles/f08.css";

export function RedactionDiff({ p, send }: { p: Props; send: Send }) {
  return (
    <>
      <span className="eyebrow">Your message, as sent and as delivered</span>
      <del className="family-bad">{text(p.original)}</del>
      <span>{text(p.delivered)}</span>
      <span className="small">policy {text(obj(p.verdict).policy_id)}</span>
      <Action label="Appeal" event="redaction.appeal" send={send} data={{ verdict: p.verdict }} />
    </>
  );
}
