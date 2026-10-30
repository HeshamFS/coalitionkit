// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { num, obj, type Props, rows, type Send, text } from "../f08/shared";
import "../../styles/f09.css";
export function ActivityStream({ p, send }: { p: Props; send: Send }) {
  const [filter, setFilter] = useState(text(p.filter) || "all");
  const items = rows(p.items).filter((i) =>
    filter === "about me" ? i.aboutMe : filter === "decisions" ? i.decision : true,
  );
  return (
    <div className="f09-activity">
      <div>
        {items.map((item, i) => {
          const actor = obj(item.actor);
          return (
            <button
              className="row f09-activity-row"
              type="button"
              key={text(item.seq) || `${i}`}
              onClick={() => send("item.open", { seq: item.seq })}
              aria-label={`${text(actor.label ?? item.actor)} ${text(item.verb)} ${text(item.object)}, ${text(item.time)}, log entry ${text(item.seq)}`}
            >
              {item.live ? (
                <span className="live-dot" />
              ) : (
                <span
                  className={`av av-xs ${actor.kind === "agent" ? "av-sq sh" : `s${num(actor.seat) || 1}`}`}
                >
                  {text(actor.initials) || text(actor.label ?? item.actor).slice(0, 1)}
                </span>
              )}
              <span className="small grow">
                {item.live ? (
                  <b>{text(actor.label ?? item.actor)}</b>
                ) : (
                  text(actor.label ?? item.actor)
                )}{" "}
                {text(item.verb)} {text(item.object)}
              </span>
              <span className="st">{text(item.time)}</span>
            </button>
          );
        })}
      </div>
      <div className="row small">
        {["all", "about me", "decisions"].map((f) => (
          <button
            type="button"
            className={`chip ${filter === f ? "chip-on" : ""}`}
            key={f}
            aria-pressed={filter === f}
            onClick={() => setFilter(f)}
          >
            {f[0]?.toUpperCase()}
            {f.slice(1)}
          </button>
        ))}
      </div>
    </div>
  );
}
