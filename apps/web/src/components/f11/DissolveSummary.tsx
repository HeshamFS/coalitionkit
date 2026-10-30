// SPDX-License-Identifier: Apache-2.0
import { obj, type Props, rows, type Send, text } from "../f08/shared";
import "../../styles/f11.css";
export function DissolveSummary({ p, send }: { p: Props; send: Send }) {
  const counts = obj(p.counts);
  return (
    <>
      <div className="row f11-summary-heading">
        <div className="col grow">
          <span className="eyebrow">{text(counts.ended)}</span>
          <b>{text(p.goal)}</b>
          <span className="small">{text(counts.summary)}</span>
        </div>
        <span className={`tag ${p.outcome === "reached" ? "t-agreed" : "t-needs"}`}>
          {p.outcome === "reached" ? "Agreed" : text(p.outcome)}
        </span>
      </div>
      <div className="g4 f11-summary-metrics">
        {["tasks", "decisions", "replans", "cost"].map((key) => (
          <div className="stage" key={key}>
            <span className="st">
              {key === "replans" ? "re-plans" : key === "cost" ? "agent cost" : key}
            </span>
            <span className="answer">
              {key === "cost" ? text(p.cost) : text(counts[key])}
              {key === "tasks" && counts.total ? ` / ${text(counts.total)}` : ""}
            </span>
            {key === "cost" && <span className="badge b-measured">metered</span>}
          </div>
        ))}
      </div>
      <div className="f11-contributions">
        {rows(p.contributions).map((c, i) => (
          <div className="row small" key={text(c.participant)}>
            <span className={`av av-xs s${[3, 1, 5][i % 3]}`}>{text(c.participant).slice(-1)}</span>
            <span>
              {text(c.participant)} · {text(c.tasks)} · {text(c.hours)} h
            </span>
          </div>
        ))}
      </div>
      <div className="row">
        <button
          type="button"
          className="btn btn-sm"
          aria-label="Download sealed log"
          onClick={() => send("log.download", { log: p.log })}
        >
          Download the sealed log
        </button>
        <button
          type="button"
          className="btn btn-sm btn-ghost"
          aria-label="Open results"
          onClick={() => send("results.open")}
        >
          Results
        </button>
        <span className="h-right small">vaults stay with each member</span>
      </div>
    </>
  );
}
