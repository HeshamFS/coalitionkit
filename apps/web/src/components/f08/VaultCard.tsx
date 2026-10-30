// SPDX-License-Identifier: Apache-2.0
import { Badge, type Props, rows, type Send, text } from "./shared";
export function VaultCard({ p, send }: { p: Props; send: Send }) {
  const policies: Record<string, string> = {
    psi: "PSI only",
    masked: "masked share",
    never: "never shared",
  };
  return (
    <>
      <div className="row">
        <svg className="ico" viewBox="0 0 24 24" aria-hidden="true">
          <rect x="5" y="11" width="14" height="10" rx="2" />
          <path d="M8 11V8a4 4 0 0 1 8 0v3" />
        </svg>
        <b style={{ fontSize: 13.5 }}>Your vault</b>
        <span className="h-right st">
          {p.location === "device" ? "local" : text(p.location)} · encrypted
        </span>
      </div>
      <div className="f08-vault-rows">
        {rows(p.categories).map((c) => (
          <div className="row" key={text(c.name)}>
            <span className="small grow" style={{ color: "var(--ink)" }}>
              {text(c.name)}
            </span>
            <span className="num small">
              {text(c.count)}
              {c.policy === "psi" ? " slots" : ""}
            </span>
            <Badge>{policies[text(c.policy)] ?? text(c.policy)}</Badge>
          </div>
        ))}
      </div>
      <div className="row">
        <span className="small">Answered {text(p.answersToday)} questions today</span>
        <details className="h-right f08-vault-menu">
          <summary className="small blue">See all</summary>
          <button type="button" className="btn btn-sm" onClick={() => send("vault.export")}>
            Export
          </button>
          <button type="button" className="btn btn-sm" onClick={() => send("vault.wipe")}>
            Wipe vault
          </button>
        </details>
      </div>
    </>
  );
}
