// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { list, obj, type Props, rows, type Send, text, usePreviewState } from "../f08/shared";
import { RippleBanner } from "./legacy";
import "../../styles/f09.css";
export function Ripple({ p, send }: { p: Props; send: Send }) {
  const preview = usePreviewState();
  const [dismissed, setDismissed] = useState(preview === "dismissed");
  const r = obj(p.ripple);
  return dismissed ? (
    <span className="st">Dismissed</span>
  ) : (
    <RippleBanner
      ripple={{
        by: text(r.by),
        change: text(r.change),
        invalidated: list(r.invalidated).map(text),
        untouched: list(r.untouched).map(text),
      }}
      onOpen={() => send("ripple.open")}
      onDismiss={() => setDismissed(true)}
    />
  );
}
export function Masks({ p, send }: { p: Props; send: Send }) {
  const [selected, setSelected] = useState(0);
  const [editing, setEditing] = useState(!rows(p.masks).some((mask) => mask.polygon));
  const masks = rows(p.masks);
  const frameTotal = masks[0]?.frame_count;
  return (
    <div className="f09-masks">
      <div className="media f09-mask-media">
        <svg
          viewBox="0 0 260 170"
          role="img"
          aria-label={p.media_ref ? "Masked media regions" : "Loading media"}
        >
          <title>Masked media regions</title>
          <rect width="260" height="170" fill="var(--f09-media-bg)" />
          <rect x="30" y="40" width="200" height="100" rx="8" fill="var(--f09-media-panel)" />
          {masks.map((mask, i) => (
            <g key={text(mask.id) || `${i}`} className={`f09-region f09-region-${i % 2}`}>
              <path d={text(mask.polygon)} fillOpacity=".35" strokeWidth="2" />
              <rect
                x={i ? 152 : 62}
                y={i ? 46 : 56}
                width="64"
                height="15"
                rx="3"
                className="f09-region-label"
              />
              <text
                x={i ? 156 : 66}
                y={i ? 57 : 67}
                fontFamily="var(--font-ui)"
                fontSize="9.5"
                fill="white"
                stroke="none"
              >
                {text(mask.label)} {text(mask.score)}
              </text>
            </g>
          ))}
          {rows(p.hidden).map((region, i) => (
            <g key={text(region.polygon) || `${i}`}>
              <path d={text(region.polygon)} fill="var(--dark-bg)" opacity=".85" />
              <text x="172" y="129" fontSize="8.5" fill="white">
                label hidden
              </text>
            </g>
          ))}
        </svg>
      </div>
      <div className="row small">
        {masks.map((mask, i) => (
          <button
            type="button"
            key={text(mask.id) || `${i}`}
            className={`chip ${selected === i ? "chip-on" : ""}`}
            aria-pressed={selected === i}
            onClick={() => setSelected(i)}
          >
            {text(mask.label)}
          </button>
        ))}
        {rows(p.labels).length > 0 && (
          <button type="button" className="chip f09-add-label" onClick={() => setEditing(!editing)}>
            + label
          </button>
        )}
        <span className="h-right st">
          frame {text(p.frame)}
          {frameTotal ? ` of ${text(frameTotal)}` : ""}
        </span>
      </div>
      {editing &&
        rows(p.labels).map((label, i) => (
          <label className="field" key={text(label.mask) || `${i}`}>
            Region {text(label.mask)}
            <input
              className="input"
              defaultValue={text(label.label)}
              onBlur={(e) => {
                if (e.target.value !== text(label.label))
                  send("mask.label", { id: label.mask, label: e.target.value });
              }}
            />
          </label>
        ))}
    </div>
  );
}
