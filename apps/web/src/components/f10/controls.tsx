// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { Action, type Props, rows, type Send, text, usePreviewState } from "../f08/shared";
import "../../styles/f10.css";

export function Capture({ p, send }: { p: Props; send: Send }) {
  const preview = usePreviewState();
  const [state, setState] = useState(preview ?? "ready");
  return (
    <div className="f10-capture" data-state={state}>
      <div className="f10-camera">
        <span className="eyebrow">{state === "recording" ? "● Recording" : state}</span>
        {rows(p.masks).map((m, i) => (
          <span className="f10-region" key={text(m.label) || `${i}`}>
            {text(m.label)} · {text(m.score)}
          </span>
        ))}
      </div>
      <span className="small">{text(p.tips)}</span>
      <button
        type="button"
        className="btn btn-ink"
        disabled={state === "done"}
        onClick={() => {
          const recording = state === "recording";
          setState(recording ? "done" : "recording");
          send(recording ? "capture.stop" : "capture.start", {
            video: p.video,
            narration: p.narration,
          });
        }}
      >
        {state === "recording"
          ? "Stop recording"
          : state === "done"
            ? "Recorded"
            : "Start recording"}
      </button>
    </div>
  );
}
export function Schedule({ p, send }: { p: Props; send: Send }) {
  const bookings = rows(p.machines).flatMap((m) => rows(m.bookings));
  const stamps = bookings
    .flatMap((b) => [Date.parse(text(b.start)), Date.parse(text(b.end))])
    .filter(Number.isFinite);
  const first = Math.min(...stamps);
  const duration = Math.max(...stamps) - first || 1;
  return (
    <>
      {rows(p.machines).map((m, i) => (
        <div className="row" key={text(m.name) || `${i}`}>
          <span className="small f10-machine">{text(m.name)}</span>
          <div className="f10-track">
            {rows(m.bookings).map((b, j) => (
              <span
                key={text(b.start) || `${j}`}
                className={`f10-booking ${b.mine ? "f10-mine" : ""}`}
                style={{
                  left: `${((Date.parse(text(b.start)) - first) / duration) * 100}%`,
                  width: `${((Date.parse(text(b.end)) - Date.parse(text(b.start))) / duration) * 100}%`,
                }}
                title={b.mine ? "This coalition" : "Busy"}
              />
            ))}
          </div>
          <Action label="Hold" event="slot.hold" send={send} data={{ machine: m.name }} />
        </div>
      ))}
      <span className="st">This coalition · other bookings shown as busy only</span>
    </>
  );
}
