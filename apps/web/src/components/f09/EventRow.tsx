// SPDX-License-Identifier: Apache-2.0
import { type Props, type Send, text, usePreviewState } from "../f08/shared";
import "../../styles/f09.css";
export function EventRow({ p, send }: { p: Props; send: Send }) {
  const selected = usePreviewState() === "selected" || Boolean(p.selected);
  const receipt = p.form === "receipt-only";
  return (
    <button
      type="button"
      data-component="EventRow"
      className={`ln f09-event ${selected ? "ln-hit" : ""}`}
      onClick={() => send("entry.open", { seq: p.seq })}
    >
      <span className="no">{text(p.seq)}</span>
      {p.ts !== undefined && (
        <time className="f09-log-time" title={text(p.ts)}>
          {text(p.ts).includes("T")
            ? new Date(text(p.ts)).toLocaleTimeString("en-GB", {
                hour: "2-digit",
                minute: "2-digit",
                timeZone: "UTC",
              })
            : text(p.ts)}
        </time>
      )}
      <span className={`f09-log-type ${receipt ? "mut3" : "blue"}`}>
        {receipt ? "· not for you ·" : text(p.type)}
      </span>
      <span className={`grow ${receipt ? "mut3" : ""}`}>
        {receipt ? "receipt only" : selected ? <b>{text(p.summary)}</b> : text(p.summary)}
        {p.form === "projection" && (
          <>
            {" "}
            <span className="badge b-signed">projection</span>
          </>
        )}
      </span>
      {p.hash !== undefined && <span className="mut3">{text(p.hash)}</span>}
    </button>
  );
}
