// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { expired, Frame, label, list, number, obj, text, type View } from "../f02/ui";
import "./receipt.css";

export function Receipt({ p, send }: View) {
  const [copied, setCopied] = useState("");
  const receipt = obj(p.receipt);
  return (
    <Frame name="Receipt" state="recorded">
      <div className="f04-receipt-card">
        <div className="f04-receipt-heading">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M5 12l5 5 9-10" />
          </svg>
          <b>Your answer is recorded</b>
        </div>
        <dl>
          <dt>Log entry</dt>
          <dd className="f04-receipt-mono">#{number(p.seq)}</dd>
          <dt>Receipt</dt>
          <dd className="f04-receipt-mono">
            {text(receipt.algorithm ?? receipt.signature)}
            {receipt.verified === true ? " ✓" : ""}
          </dd>
          <dt>Hash</dt>
          <dd className="f04-receipt-mono">{text(p.hash)}</dd>
          <dt>Waiting for</dt>
          <dd>{list(p.remaining).map(label).join(", ") || "Nobody"}</dd>
        </dl>
        <div className="f04-receipt-actions">
          <button
            className="ck-action"
            type="button"
            onClick={() => send("receipt.verify", { receipt: p.receipt, hash: p.hash })}
          >
            Verify myself
          </button>
          <button
            className="ck-action"
            type="button"
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(
                  JSON.stringify({ seq: p.seq, receipt: p.receipt, hash: p.hash }),
                );
                setCopied("Copied");
              } catch {
                setCopied("Copy unavailable");
              }
            }}
          >
            Copy
          </button>
          <span role="status">{copied}</span>
        </div>
      </div>
      <div className="f04-receipt-toast">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M5 12l5 5 9-10" />
        </svg>
        <span>Signed. You can change it until the deadline</span>
        <button
          type="button"
          aria-label="Change answer"
          disabled={expired(p.decision_deadline)}
          onClick={() => send("decide.change", { subject: p.subject })}
        >
          Change
        </button>
      </div>
    </Frame>
  );
}
