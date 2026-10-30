// SPDX-License-Identifier: Apache-2.0
import { Badge, type Props, rows, type Send, text } from "../f08/shared";
import "../../styles/f11.css";

export function CoalitionArchive({ p, send }: { p: Props; send: Send }) {
  return rows(p.items).length ? (
    rows(p.items).map((item, i) => (
      <button
        type="button"
        className="f11-archive"
        key={text(item.coalition) || `${i}`}
        onClick={() => send("archive.open", { id: item.coalition })}
      >
        <b>{text(item.coalition)}</b>
        <span className="small">
          {text(item.ended)} · {text(item.pack)}
        </span>
        <Badge tone="measured">{text(item.outcome)}</Badge>
        <span className="num">{text(item.yourCost)}</span>
      </button>
    ))
  ) : (
    <div className="f11-empty">
      <b>No past coalitions yet</b>
      <p className="small">When a coalition ends, its results and signed log appear here.</p>
    </div>
  );
}
