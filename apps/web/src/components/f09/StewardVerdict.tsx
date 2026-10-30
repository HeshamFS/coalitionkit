// SPDX-License-Identifier: Apache-2.0
import { Action, Badge, Fields, obj, type Props, type Send, text } from "../f08/shared";
import "../../styles/f09.css";

export function StewardVerdict({ p, send }: { p: Props; send: Send }) {
  {
    const v = obj(p.verdict);
    return (
      <>
        <div className="row">
          <b>Steward verdict</b>
          <Badge tone="signed">{text(v.action)}</Badge>
        </div>
        <Fields
          values={{
            Event: v.event_id,
            Policy: v.policy_id,
            Explanation: v.explain,
            Redacted: v.redact,
          }}
        />
        <Action
          label="Verify signature"
          event="verdict.verify"
          send={send}
          data={{ verdict: p.verdict }}
        />
      </>
    );
  }
}
