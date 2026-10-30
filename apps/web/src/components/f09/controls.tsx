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
  return (
    <>
      <div
        className="f09-media"
        role="img"
        aria-label={p.media_ref ? "Masked media regions" : "Loading media"}
      >
        <span className="st">{p.media_ref ? text(p.media_ref) : "Loading…"}</span>
        {rows(p.masks).map((mask, i) => (
          <div className={`f09-mask f09-mask-${i % 3}`} key={text(mask.id) || `${i}`}>
            {text(mask.label)} · {text(mask.score)}
          </div>
        ))}
      </div>
      {rows(p.labels).map((label, i) => (
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
    </>
  );
}
