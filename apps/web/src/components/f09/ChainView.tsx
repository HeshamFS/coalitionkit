// SPDX-License-Identifier: Apache-2.0
import { Action, Badge, type Props, rows, type Send, text } from "../f08/shared";
import "../../styles/f09.css";

export function ChainView({ p, send }: { p: Props; send: Send }) {
  return (
    <>
      <span className="st mono">genesis {text(p.genesis)}</span>
      <div className="f09-chain">
        {rows(p.entries).map((e, i) => (
          <div
            className={`card ${e.verified === false ? "f09-broken" : ""}`}
            key={text(e.seq) || `${i}`}
          >
            <b>
              #{text(e.seq)} · {text(e.type)}
            </b>
            <span className="mono small">
              {text(e.prev_hash)} → {text(e.hash)}
            </span>
            <Badge tone={e.verified ? "signed" : "estimate"}>
              {e.verified ? "✓ verified" : "broken"}
            </Badge>
          </div>
        ))}
      </div>
      <Action label="Verify chain" event="chain.verify" send={send} />
    </>
  );
}
