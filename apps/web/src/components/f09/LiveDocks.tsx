// SPDX-License-Identifier: Apache-2.0
import { type Props, rows, type Send, text } from "../f08/shared";
import "../../styles/f09.css";

export function LiveDocks({ p, send }: { p: Props; send: Send }) {
  return (
    <div className="row wrap">
      {rows(p.docks).map((d, i) => (
        <button
          type="button"
          className="dock"
          key={text(d.ref) || `${i}`}
          onClick={() => send("dock.open", { ref: d.ref })}
        >
          {text(d.label)} <b>{text(d.value)}</b>
        </button>
      ))}
    </div>
  );
}
