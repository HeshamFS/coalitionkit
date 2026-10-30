// SPDX-License-Identifier: Apache-2.0
import { type Props, type Send, text } from "../f08/shared";
import "../../styles/f09.css";

export function ReceiptBadge({ p, send }: { p: Props; send: Send }) {
  return (
    <button
      type="button"
      className={`badge b-${p.state === "ok" ? "signed" : "estimate"}`}
      onClick={() => send("receipt.verify", { seq: p.seq })}
    >
      #{text(p.seq)} · {text(p.state)}
    </button>
  );
}
