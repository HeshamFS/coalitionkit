// SPDX-License-Identifier: Apache-2.0
import { Fragment } from "react";
import { list, num, type Props, rows, type Send } from "../f08/shared";
import { EventRow } from "./EventRow";
import "../../styles/f09.css";
export function LogStream({ p, send }: { p: Props; send: Send }) {
  const entries = rows(p.entries).filter(
    (e) => !list(p.filter).length || list(p.filter).includes(e.type),
  );
  return (
    <div className="code">
      <div className="code-head">
        <span>coalition log · your projection</span>
        <span className="h-right row">
          <span className="chip">all types</span>
          <span className="badge b-signed">chain ✓</span>
        </span>
      </div>
      {entries.map((entry, i) => (
        <Fragment key={num(entry.seq)}>
          {i > 0 && num(entry.seq) > num(entries[i - 1]?.seq) + 1 && (
            <div className="ln mut3">
              … gap: #{num(entries[i - 1]?.seq) + 1}–#{num(entry.seq) - 1} not in your projection
            </div>
          )}
          <EventRow p={entry} send={send} />
        </Fragment>
      ))}
    </div>
  );
}
