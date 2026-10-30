// SPDX-License-Identifier: Apache-2.0
import { list, type Props, type Send, text } from "../f08/shared";
import "../../styles/f09.css";
export function EvidenceCard({ p, send }: { p: Props; send: Send }) {
  return (
    <button
      type="button"
      className="card f09-evidence"
      aria-label="Open evidence"
      onClick={() => send("evidence.open", { ref: p.ref })}
    >
      <div className="media f09-evidence-media">
        <svg
          viewBox="0 0 200 110"
          role="img"
          aria-label={list(p.masks).length ? "Masked evidence preview" : "Evidence preview"}
        >
          <title>Evidence preview</title>
          <ellipse cx="100" cy="70" rx="46" ry="16" fill="var(--f09-object-shadow)" />
          <rect x="70" y="40" width="60" height="30" rx="4" fill="var(--f09-object)" />
          <text
            x="8"
            y="16"
            fontFamily="var(--font-mono)"
            fontSize="8"
            fill="var(--f09-media-text)"
          >
            {text(p.captured_at)}
          </text>
          {list(p.masks).length > 0 && (
            <rect x="70" y="40" width="60" height="30" fill="var(--dark-bg)" />
          )}
        </svg>
      </div>
      <div className="row">
        <span className="h-title">{text(p.task)}</span>
        <span className="h-right badge b-measured">Measured</span>
      </div>
      <dl className="kv">
        <dt>Kind</dt>
        <dd>{text(p.kind)}</dd>
        <dt>Verified by</dt>
        <dd>{text(p.verified_by)}</dd>
        <dt>Ref</dt>
        <dd className="mono">{text(p.ref)}</dd>
      </dl>
    </button>
  );
}
