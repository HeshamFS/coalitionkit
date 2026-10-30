// SPDX-License-Identifier: Apache-2.0
import { Badge, type Props, type Send, text } from "./shared";
export function PrivateField({ p, send }: { p: Props; send: Send }) {
  const masked = text(p.display).includes("•");
  return (
    <>
      <div className="row">
        <Badge tone="vault">{text(p.policy) || "vault"}</Badge>
      </div>
      <div className="input">
        <span className="grow">
          {masked ? <span className="redact" style={{ width: 46 }} /> : text(p.display)}
        </span>
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
      </div>
      <span className="help">
        Hidden on screen too · tap the eye to show for {text(p.reveal) || "10"} s
      </span>
    </>
  );
}
