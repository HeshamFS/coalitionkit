// SPDX-License-Identifier: Apache-2.0
import { Badge, Bar, list, num, obj, type Props, rows, type Send, text } from "./shared";
export function VoteTally({ p }: { p: Props; send: Send }) {
  const deciders = list(p.deciders);
  return p.outcome ? (
    <>
      <div className="row">
        <b style={{ fontSize: 12.5 }}>Closed · {text(p.outcome)}</b>
        {p.outcome === "split" && (
          <span className="h-right">
            <Badge>re-planning</Badge>
          </span>
        )}
      </div>
      <div className="row small">
        {rows(p.answers).map((a, i) => (
          <span
            className="badge"
            key={text(a.participant) || i}
            style={{
              background: a.answer ? "var(--ok-bg)" : "var(--bad-bg)",
              color: a.answer ? "var(--ok-fg)" : "var(--bad-fg)",
            }}
          >
            {text(a.participant).split(" ").at(-1)} {a.answer ? "yes" : "no"}
          </span>
        ))}
      </div>
    </>
  ) : (
    <>
      <div className="row">
        <b style={{ fontSize: 13 }}>{text(obj(p.subject).id)}</b>
        <span className="h-right small">rule: {text(p.rule)}</span>
      </div>
      <div className="row" style={{ gap: 6 }}>
        {deciders.map((d, i) => (
          <span
            key={text(d) || i}
            className={`av av-lg s${[3, 1, 5][i % 3]}`}
            style={{
              boxShadow: `0 0 0 2px var(--surface),0 0 0 4px ${i < num(p.answered) ? "var(--ok-fg)" : "var(--line-strong)"}`,
            }}
            role="img"
            aria-label={text(d)}
          >
            {text(d).split(" ").at(-1)?.slice(0, 1)}
          </span>
        ))}
      </div>
      <div className="row small">
        <span className="num">
          <b>{text(p.answered)}</b> answered ·{" "}
          <b>{Math.max(0, deciders.length - num(p.answered))}</b> waiting
        </span>
      </div>
      <Bar value={num(p.answered) / Math.max(1, deciders.length)} />
      <span className="st">how each member answered is shown when the decision closes</span>
    </>
  );
}
