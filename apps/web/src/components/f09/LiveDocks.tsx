// SPDX-License-Identifier: Apache-2.0
import { type Props, rows, type Send, text } from "../f08/shared";
import "../../styles/f09.css";
export function LiveDocks({ p, send }: { p: Props; send: Send }) {
  return (
    <div className="col">
      {rows(p.docks).map((d, i) => (
        <button
          type="button"
          className="dock"
          key={text(d.ref) || `${i}`}
          onClick={() => send("dock.open", { ref: d.ref })}
        >
          {Boolean(d.icon) && (
            <svg className="ico ico-sm" viewBox="0 0 24 24" aria-hidden="true">
              <path
                d={
                  d.icon === "shield"
                    ? "M12 3l8 4v6c0 4-3.5 7-8 8-4.5-1-8-4-8-8V7z"
                    : "M4 4h16v16H4z"
                }
              />
            </svg>
          )}
          {text(d.prefix)}
          <b>{text(d.value)}</b>
          {text(d.label)}
        </button>
      ))}
    </div>
  );
}
