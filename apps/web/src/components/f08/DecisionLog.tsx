// SPDX-License-Identifier: Apache-2.0
import { Badge, type Props, rows, type Send, text } from "./shared";
import "../../styles/f08.css";

export function DecisionLog({ p, send }: { p: Props; send: Send }) {
  return (
    <>
      {rows(p.entries).map((e, i) => (
        <button
          type="button"
          className="f08-decision"
          key={text(e.seq) || `${i}`}
          onClick={() => send("entry.open", { seq: e.seq })}
        >
          <span>{text(e.time)}</span>
          <b>{text(e.participant)}</b>
          <span>
            {text(e.subject)} · r{text(e.revision)}
          </span>
          <Badge tone="signed">
            {text(e.answer)} {e.verified ? "✓" : ""}
          </Badge>
        </button>
      ))}
    </>
  );
}
