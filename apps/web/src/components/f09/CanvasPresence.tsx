// SPDX-License-Identifier: Apache-2.0
import { type Props, rows, type Send, text } from "../f08/shared";
import "../../styles/f09.css";

export function CanvasPresence({ p }: { p: Props; send: Send }) {
  return (
    <div className="f09-presence">
      {rows(p.cursors).map((c, i) => (
        <div className={`f09-cursor s${(i % 5) + 1}`} key={text(c.actor) || `${i}`}>
          <span>↖ {text(c.actor)}</span>
          <small>
            {text(c.verb)} · {text(c.target)}
          </small>
        </div>
      ))}
    </div>
  );
}
