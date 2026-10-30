// SPDX-License-Identifier: Apache-2.0
import { Bar, Fields, num, type Props, type Send, text } from "../f08/shared";
import "../../styles/f10.css";
export function EdgeReaderStatus({ p }: { p: Props; send: Send }) {
  const confidence = num(p.confidence);
  return (
    <>
      <div className="row">
        <span className="live-dot" />
        <b className="f10-reader-title">
          {confidence >= 0.8
            ? `Reading the display by ${text(p.source)}`
            : confidence > 0
              ? "Low confidence"
              : "Reader lost"}
        </b>
      </div>
      <Fields
        values={{
          [p.source === "camera" ? "Camera" : "Source"]:
            `${text(p.source)} · ${text(p.rate)} ${p.source === "camera" ? "fps" : "Hz"}`,
          Confidence: text(p.confidence),
          "Frames kept": p.framesKept ?? "none",
          Fallback: p.fallback,
        }}
      />
      <Bar value={confidence} />
    </>
  );
}
