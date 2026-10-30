// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { Action, Badge, obj, type Props, rows, type Send, text } from "../f08/shared";
import "../../styles/f11.css";

export function Channels({ p, send }: { p: Props; send: Send }) {
  const quiet = obj(p.quiet);
  const [from, setFrom] = useState(text(quiet.from));
  const [to, setTo] = useState(text(quiet.to));
  return (
    <>
      {rows(p.channels).map((c, i) => (
        <label className="row" key={text(c.kind) || `${i}`}>
          <span className="grow">{text(c.kind)}</span>
          <select
            className="input"
            defaultValue={text(c.level)}
            onChange={(e) => send("channel.set", { kind: c.kind, level: e.target.value })}
          >
            {["everything", "needs-you", "next-step", "digest", "off"].map((level) => (
              <option key={level}>{level}</option>
            ))}
          </select>
        </label>
      ))}
      <fieldset className="f11-quiet">
        <legend>Quiet hours · {text(quiet.tz)}</legend>
        <label>
          From
          <input type="time" value={from} onChange={(e) => setFrom(e.target.value)} />
        </label>
        <label>
          To
          <input type="time" value={to} onChange={(e) => setTo(e.target.value)} />
        </label>
        <Action
          label="Save quiet hours"
          event="quiet.set"
          send={send}
          data={{ from, to, tz: quiet.tz }}
        />
      </fieldset>
    </>
  );
}
export function Lessons({ p, send }: { p: Props; send: Send }) {
  const [selected, setSelected] = useState(rows(p.lessons).map(() => true));
  return (
    <>
      {rows(p.lessons).map((lesson, i) => (
        <label className="card" key={text(lesson.text) || `${i}`}>
          <span className="row">
            <input
              type="checkbox"
              checked={selected[i] ?? false}
              onChange={(e) =>
                setSelected((old) => old.map((v, j) => (j === i ? e.target.checked : v)))
              }
            />
            <span>{text(lesson.text)}</span>
          </span>
          <span className="row">
            <Badge tone="vault">{text(lesson.scope)}</Badge>
            <span className="st">from {text(lesson.from)}</span>
          </span>
        </label>
      ))}
      <Action
        label="Save selected lessons"
        event="lessons.save"
        send={send}
        data={{ lessons: rows(p.lessons).filter((_, i) => selected[i]) }}
        primary
      />
    </>
  );
}
export function Metric({ p }: { p: Props }) {
  return (
    <div className="f11-metric">
      <span className="st">{text(p.label)}</span>
      <strong className="answer">
        {p.value === undefined ? "—" : text(p.value)} <small>{text(p.unit)}</small>
      </strong>
      <span className="small">{p.value === undefined ? "Not run yet" : text(p.context)}</span>
      {Boolean(p.run) && <Badge tone="measured">{text(p.run)}</Badge>}
    </div>
  );
}
