// SPDX-License-Identifier: Apache-2.0
import { Badge, type Props, type Send, text } from "../f08/shared";
import "../../styles/f09.css";

export function EventRow({ p, send }: { p: Props; send: Send }) {
  return (
    <button type="button" className="f09-event" onClick={() => send("entry.open", { seq: p.seq })}>
      <span className="num">{text(p.seq)}</span>
      <span>{p.form === "receipt-only" ? "not for you" : text(p.type)}</span>
      <span>{p.form === "receipt-only" ? "Receipt only" : text(p.summary)}</span>
      <Badge tone="signed">{text(p.form)}</Badge>
    </button>
  );
}
