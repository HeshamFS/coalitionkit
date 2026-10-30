// SPDX-License-Identifier: Apache-2.0
import { useContext, useId } from "react";
import { PrivacyFieldLayout } from "./presentation";
import { Badge, num, type Props, type Send, text } from "./shared";
export function PrivateField({ p, send }: { p: Props; send: Send }) {
  const { label, unit } = useContext(PrivacyFieldLayout);
  const id = useId();
  const revealable = num(p.reveal) > 0;
  const masked = /^[•\s]+$/.test(text(p.display));
  return (
    <div className="field f08-field">
      <div className="row f08-field-label" id={id}>
        {label}
        <Badge tone={p.policy === "shared with task" ? "estimate" : "vault"}>
          {text(p.policy) || "vault"}
        </Badge>
      </div>
      <div
        className={`input${p.policy === "never shared" ? " input-dis" : ""}`}
        role="group"
        aria-labelledby={id}
      >
        <span>{masked ? <span className="redact" style={{ width: 46 }} /> : text(p.display)}</span>
        {unit && <span className="unit">{unit}</span>}
        {revealable && (
          <button
            type="button"
            className="f08-eye"
            aria-label="Reveal"
            onClick={() => send("field.reveal", { seconds: p.reveal })}
          >
            <svg className="ico ico-sm" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          </button>
        )}
      </div>
      {revealable && (
        <span className="help">
          Hidden on screen too · tap the eye to show for {text(p.reveal) || "10"} s
        </span>
      )}
    </div>
  );
}
