// SPDX-License-Identifier: Apache-2.0
import { type Props, type Send, text } from "../f08/shared";
import "../../styles/f09.css";
export function ReceiptBadge({ p, send }: { p: Props; send: Send }) {
  return (
    <button
      type="button"
      aria-label={`receipt ${text(p.state)}`}
      className={`badge f09-receipt b-${p.state === "ok" ? "signed" : p.state === "bad" ? "bad" : "estimate"}`}
      onClick={() => send("receipt.verify", { seq: p.seq })}
    >
      {p.state === "ok"
        ? `receipt #${text(p.seq)} ✓`
        : p.state === "bad"
          ? "receipt ✗ bad signature"
          : "receipt pending"}
    </button>
  );
}
