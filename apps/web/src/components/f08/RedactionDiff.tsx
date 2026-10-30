// SPDX-License-Identifier: Apache-2.0
import { Action, Badge, obj, type Props, type Send, text } from "./shared";

export function RedactionDiff({ p, send }: { p: Props; send: Send }) {
  const original = text(p.original);
  const delivered = text(p.delivered).replace(/\s*▰+$/, "");
  const prefix = original.startsWith(delivered) ? delivered : "";
  return (
    <>
      <span className="eyebrow">Your message, as sent and as delivered</span>
      <div className="small f08-message">
        {prefix} <del>{original.slice(prefix.length)}</del>
      </div>
      <div className="small f08-message">
        {delivered} <span className="redact" style={{ width: 120 }} />
      </div>
      <div className="row small">
        <Badge tone="signed">steward</Badge>policy {text(obj(p.verdict).policy_id)} · paths{" "}
        {text(obj(p.verdict).paths)}
      </div>
      <div className="row">
        <Action label="Appeal" event="redaction.appeal" send={send} data={{ verdict: p.verdict }} />
        <span className="h-right small">others see only the second line</span>
      </div>
    </>
  );
}
