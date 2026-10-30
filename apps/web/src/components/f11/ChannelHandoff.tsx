// SPDX-License-Identifier: Apache-2.0
import { obj, type Props, type Send, text, usePreviewState } from "../f08/shared";
import "../../styles/f11.css";
export function ChannelHandoff({ p, send }: { p: Props; send: Send }) {
  const preview = usePreviewState(),
    subject = obj(p.subject);
  if (preview === "expired")
    return <span className="small">This handoff expired. Review the current request.</span>;
  return (
    <>
      <div className="f11-lens">
        <span className="mono">{text(p.from).toUpperCase()}</span>
        <b>Approve {text(subject.id)}?</b>
        <span>
          {p.reason === "money" ? "Money" : p.reason === "identity" ? "Identity" : "This request"}{" "}
          needs your {text(p.to)}
        </span>
      </div>
      <div className="row f11-handoff-arrow">
        <svg className="ico" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 5v14M6 13l6 6 6-6" />
        </svg>
      </div>
      <div className="card card-ask">
        <span className="st">
          {text(p.to).toUpperCase()} · opened from {text(p.from)}
        </span>
        <b>Approve: {text(subject.id)}</b>
        <button
          type="button"
          className="btn btn-primary"
          aria-label={`Open ${text(p.to)}`}
          onClick={() => send("handoff.open", { subject: p.subject, from: p.from, to: p.to })}
        >
          Open to approve
        </button>
      </div>
    </>
  );
}
