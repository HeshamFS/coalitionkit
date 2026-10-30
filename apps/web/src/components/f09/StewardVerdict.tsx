// SPDX-License-Identifier: Apache-2.0
import { obj, type Props, type Send, text } from "../f08/shared";
import "../../styles/f09.css";

const tones: Record<string, string> = {
  allow: "measured",
  redact: "warn",
  block: "bad",
  quarantine: "estimate",
  escalate: "model",
};
export function StewardVerdict({ p, send }: { p: Props; send: Send }) {
  const v = obj(p.verdict);
  return (
    <div className="card f09-verdict">
      <div className="row">
        <span className="av av-sq sh">S</span>
        <b>Steward verdict</b>
        <button
          type="button"
          className="h-right badge b-signed f09-receipt"
          aria-label="Verify signature"
          onClick={() => send("verdict.verify", { verdict: p.verdict })}
        >
          signed
        </button>
      </div>
      <dl className="kv">
        <dt>On</dt>
        <dd>
          {text(v.event_id)} · r{text(v.revision)}
        </dd>
        <dt>Action</dt>
        <dd>
          <span className={`badge b-${tones[text(v.action)]}`}>{text(v.action)}</span>
        </dd>
        <dt>Policies</dt>
        <dd>{text(v.policy_id)}</dd>
        <dt>Model audit</dt>
        <dd>{v.model_audited ? "yes · no finding" : "no"}</dd>
        <dt>Why</dt>
        <dd>{text(v.explain)}</dd>
      </dl>
      <div className="row wrap">
        {Object.entries(tones).map(([action, tone]) => (
          <span className={`badge b-${tone}`} key={action}>
            {action}
          </span>
        ))}
      </div>
    </div>
  );
}
