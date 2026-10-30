// SPDX-License-Identifier: Apache-2.0
import { Action, obj, type Props, rows, type Send, text } from "../f08/shared";
import "../../styles/f09.css";
export function VerifyPanel({ p, send }: { p: Props; send: Send }) {
  const exported = obj(p.export);
  return (
    <div className="g2 f09-verify">
      <div className="col">
        {rows(p.checks).map((check, i) => (
          <div className="row small" key={text(check.name) || `${i}`}>
            {check.state === "passed" ? (
              <svg className="ico ico-sm family-ok" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M5 12l5 5 9-10" />
              </svg>
            ) : check.state === "failed" ? (
              <span className="family-bad">×</span>
            ) : (
              <span className="spinner" />
            )}
            <span title={text(check.detail)}>{text(check.name)}</span>
          </div>
        ))}
      </div>
      <div className="col">
        <div className="wire">
          <div>
            <span className="c">$</span> coalitionkit verify {text(exported.log)}
          </div>
          <div>
            <span className="s">✓</span> {text(exported.chain_summary)} ·{" "}
            <span className="s">✓</span> {text(exported.receipt_summary)}
          </div>
          <div>
            <span className="s">✓</span> {text(exported.projection_summary)} ·{" "}
            <span className="k">host</span> {text(exported.host_key)}
          </div>
        </div>
        <div className="row">
          <Action
            label="Download log"
            event="log.download"
            send={send}
            data={{ export: p.export }}
          />
          <button
            type="button"
            className="btn btn-sm btn-ghost"
            aria-label="Run verification: How this works"
            onClick={() => send("verify.run", { export: p.export })}
          >
            How this works
          </button>
        </div>
      </div>
    </div>
  );
}
