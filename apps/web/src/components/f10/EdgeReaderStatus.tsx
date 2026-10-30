// SPDX-License-Identifier: Apache-2.0
import { Bar, Fields, num, type Props, type Send } from "../f08/shared";
import "../../styles/f10.css";

export function EdgeReaderStatus({ p }: { p: Props; send: Send }) {
  return (
    <>
      <div className="row">
        <span className="live-dot" />
        <b>
          {num(p.confidence) >= 0.8
            ? "Reading the display"
            : num(p.confidence) > 0
              ? "Low confidence"
              : "Reader lost"}
        </b>
      </div>
      <Fields
        values={{
          Source: p.source,
          Rate: p.rate,
          Confidence: p.confidence,
          "Frames kept": p.framesKept ?? "none",
          Fallback: p.fallback,
        }}
      />
      <Bar value={num(p.confidence)} />
    </>
  );
}
