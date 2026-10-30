// SPDX-License-Identifier: Apache-2.0
import { type Props, rows, type Send, text } from "./shared";
export function DecisionLog({ p, send }: { p: Props; send: Send }) {
  return (
    <div className="f08-log">
      {rows(p.entries).map((e, i) => (
        <button
          type="button"
          className="row f08-decision"
          key={text(e.seq) || i}
          onClick={() => send("entry.open", { seq: e.seq })}
        >
          <span className="num st" style={{ width: 44 }}>
            {text(e.time)}
          </span>
          <span
            className={`av av-xs ${e.participant === "Host" ? "av-sq sh" : `s${[3, 1, 5][i % 3]}`}`}
            style={{ marginTop: 2 }}
          >
            {text(e.participant).split(" ").at(-1)?.slice(0, 1)}
          </span>
          <span className="col grow" style={{ gap: 1 }}>
            <span className="small" style={{ color: "var(--ink)" }}>
              {e.answer ? (
                <>
                  <b>{text(e.answer).replace(/^./, (s) => s.toUpperCase())}</b> to {text(e.subject)}{" "}
                  r{text(e.revision)}
                </>
              ) : (
                text(e.subject)
              )}
            </span>
            {e.reason !== undefined && <span className="st">{text(e.reason)}</span>}
          </span>
          <span className="mono st">
            #{text(e.seq)} {e.verified ? "✓" : ""}
          </span>
        </button>
      ))}
    </div>
  );
}
