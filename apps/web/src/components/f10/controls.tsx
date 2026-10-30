// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { type Props, rows, type Send, text, usePreviewState } from "../f08/shared";
import "../../styles/f10.css";

export function Capture({ p, send }: { p: Props; send: Send }) {
  const preview = usePreviewState();
  const [state, setState] = useState(preview ?? "ready");
  const masks = rows(p.masks);
  return (
    <div className="f10-capture" data-state={state}>
      <div className="f10-phone">
        <div className="f10-phone-bar">
          <span>{text(masks[0]?.time)}</span>
          <span className="row">
            <span className="f10-rec-dot" />
            {state === "recording" ? "REC" : state.toUpperCase()} {text(masks[0]?.elapsed)}
          </span>
        </div>
        <div className="f10-camera">
          <svg viewBox="0 0 250 260" role="img" aria-label="Device capture with detected controls">
            <rect x="50" y="60" width="150" height="120" rx="8" fill="var(--f10-device)" />
            <rect x="70" y="80" width="70" height="40" rx="3" fill="var(--f10-display)" />
            <text x="78" y="105" className="f10-display-value">
              {text(masks[0]?.reading)}
            </text>
            <circle cx="170" cy="95" r="10" fill="var(--f10-dial)" />
            <circle cx="170" cy="130" r="10" fill="var(--f10-dial)" />
            {masks.map((mask, i) => (
              <g key={text(mask.label)}>
                {i === 0 ? (
                  <>
                    <rect
                      x="66"
                      y="78"
                      width="78"
                      height="46"
                      rx="4"
                      fill="none"
                      stroke="var(--dark-blue)"
                      strokeWidth="2"
                    />
                    <text x="66" y="72" className="f10-mask-label">
                      {text(mask.label)} · {text(mask.score)}
                    </text>
                  </>
                ) : (
                  <>
                    <circle
                      cx="170"
                      cy="95"
                      r="14"
                      fill="none"
                      stroke="var(--f10-mask-dial)"
                      strokeWidth="2"
                    />
                    <text x="186" y="92" className="f10-dial-label">
                      {text(mask.label)}
                    </text>
                  </>
                )}
              </g>
            ))}
          </svg>
          <span className="f10-narration">{text(p.narration)}</span>
        </div>
        <div className="f10-record-controls">
          <button
            type="button"
            className="f10-record"
            aria-label={
              state === "recording"
                ? "Stop recording"
                : state === "done"
                  ? "Recorded"
                  : "Start recording"
            }
            disabled={state === "done"}
            title={text(p.tips)}
            onClick={() => {
              const recording = state === "recording";
              setState(recording ? "done" : "recording");
              send(recording ? "capture.stop" : "capture.start", {
                video: p.video,
                narration: p.narration,
              });
            }}
          >
            <span />
          </button>
        </div>
      </div>
    </div>
  );
}
export function Schedule({ p, send }: { p: Props; send: Send }) {
  const machines = rows(p.machines),
    bookings = machines.flatMap((m) => rows(m.bookings));
  const stamps = bookings
    .flatMap((b) => [Date.parse(text(b.start)), Date.parse(text(b.end))])
    .filter(Number.isFinite);
  const first = stamps.length ? Math.floor(Math.min(...stamps) / 86400000) * 86400000 : 0;
  const duration = Math.max(4 * 86400000, Math.max(...stamps) - first);
  return (
    <>
      <div className="f10-schedule">
        {machines.map((m, i) => (
          <div className="row small" key={text(m.name)}>
            <span className="f10-machine">{text(m.name)}</span>
            <button
              type="button"
              className="f10-track"
              aria-label={`Hold ${text(m.name)}`}
              onClick={() => send("slot.hold", { machine: m.name })}
            >
              {rows(m.bookings).map((b, j) => (
                <span
                  key={text(b.start) || j}
                  className={`f10-booking ${b.mine ? "f10-mine" : b.local ? `f10-local-${i % 3}` : ""}`}
                  style={{
                    left: `${((Date.parse(text(b.start)) - first) / duration) * 100}%`,
                    width: `${((Date.parse(text(b.end)) - Date.parse(text(b.start))) / duration) * 100}%`,
                  }}
                  title={b.mine ? "This coalition" : "Busy"}
                />
              ))}
            </button>
          </div>
        ))}
        <div className="row sp st f10-days">
          {[0, 1, 2, 3].map((i) => (
            <span key={i}>
              {new Date(first + i * 86400000).toLocaleDateString("en-GB", {
                weekday: "short",
                timeZone: "UTC",
              })}
            </span>
          ))}
        </div>
      </div>
      <div className="row small">
        <span className="row">
          <span className="f10-schedule-key f10-mine" />
          this coalition
        </span>
        <span className="row">
          <span className="f10-schedule-key f10-busy" />
          booked elsewhere
        </span>
      </div>
    </>
  );
}
