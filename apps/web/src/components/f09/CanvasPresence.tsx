// SPDX-License-Identifier: Apache-2.0
import { num, obj, type Props, rows, type Send, text } from "../f08/shared";
import "../../styles/f09.css";
export function CanvasPresence({ p }: { p: Props; send: Send }) {
  const cursors = rows(p.cursors);
  return (
    <div className="stage stage-dots f09-presence">
      {cursors.map((c, i) => {
        const target = obj(c.target);
        const seat = text(c.seat) || `${(i % 5) + 1}`;
        return (
          <div key={text(c.actor) || `${i}`}>
            {Boolean(target.title) && (
              <div
                className={`card f09-presence-card ${target.changed ? "card-live" : ""}`}
                style={{
                  left: num(target.x),
                  top: num(target.y),
                  width: num(target.width) || 190,
                  outline:
                    c.kind === "agent" && c.verb === "editing"
                      ? `2px dashed var(--seat-${seat})`
                      : undefined,
                }}
              >
                <span className="h-title">{text(target.title)}</span>
                <span className="small">{text(target.detail)}</span>
              </div>
            )}
            <div
              className="f09-cursor"
              style={{
                left: num(c.x),
                top: num(c.y),
                color: seat === "h" ? "var(--ink)" : `var(--seat-${seat})`,
              }}
            >
              <svg width="14" height="16" viewBox="0 0 14 16" aria-hidden="true">
                <path d="M1 1l11 6-5 1.5L5 14z" fill="currentColor" />
              </svg>
              <span className={`cursor-tag s${seat}`}>
                {text(c.actor)}
                {c.kind === "agent" && c.verb === "editing" ? " · agent" : ""}
              </span>
            </div>
          </div>
        );
      })}
      {cursors.length > 0 && (
        <span className="dock f09-here">
          <span className="stack">
            {[...cursors]
              .sort((a, b) => text(a.initials).localeCompare(text(b.initials)))
              .map((c, i) => (
                <span
                  key={text(c.actor) || `${i}`}
                  className={`av av-xs ${c.kind === "agent" ? "av-sq" : ""} s${text(c.seat) || i + 1}`}
                >
                  {text(c.initials) || text(c.actor).slice(0, 1)}
                </span>
              ))}
          </span>
          <b>{cursors.length} here</b>
        </span>
      )}
    </div>
  );
}
