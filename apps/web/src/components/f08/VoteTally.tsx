// SPDX-License-Identifier: Apache-2.0
import { Badge, Bar, list, num, obj, type Props, rows, type Send, text } from "./shared";
import "../../styles/f08.css";

export function VoteTally({ p }: { p: Props; send: Send }) {
  {
    const deciders = list(p.deciders);
    return p.outcome ? (
      <>
        <b>Closed · {text(p.outcome)}</b>
        <div className="row wrap">
          {rows(p.answers).map((a, i) => (
            <Badge key={text(a.participant) || `${i}`} tone={a.answer ? "measured" : "estimate"}>
              {text(a.participant)} {a.answer ? "yes" : "no"}
            </Badge>
          ))}
        </div>
      </>
    ) : (
      <>
        <div className="row">
          <b>{text(obj(p.subject).id)}</b>
          <span className="h-right small">rule: {text(p.rule)}</span>
        </div>
        <div className="row">
          {deciders.map((d, i) => (
            <span
              key={text(d) || `${i}`}
              className={`av av-lg s${(i % 5) + 1}`}
              role="img"
              aria-label={text(d)}
            >
              {text(d).slice(0, 1)}
            </span>
          ))}
        </div>
        <span>
          {text(p.answered)} answered · {Math.max(0, deciders.length - num(p.answered))} waiting
        </span>
        <Bar value={num(p.answered) / Math.max(1, deciders.length)} />
        <span className="st">How each decider answered is shown when the decision closes</span>
      </>
    );
  }
}
