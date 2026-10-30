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
  const lessons = rows(p.lessons);
  const [selected, setSelected] = useState(lessons.map((l) => l.kind !== "judgement"));
  return (
    <>
      <div className="f11-lessons">
        {lessons.map((lesson, i) => (
          <label
            className={`card f11-lesson${lesson.kind === "judgement" ? " card-dashed" : ""}`}
            key={text(lesson.text) || `${i}`}
          >
            <input
              type="checkbox"
              checked={selected[i] ?? false}
              disabled={lesson.kind === "judgement"}
              onChange={(e) =>
                setSelected((old) => old.map((v, j) => (j === i ? e.target.checked : v)))
              }
            />
            <span className="col grow">
              <span className="small">
                {lesson.kind === "judgement" ? text(lesson.text) : <b>{text(lesson.text)}</b>}
              </span>
              <span className="st">
                {lesson.kind === "judgement"
                  ? "rejected by default: judgements about people are not stored"
                  : `from: ${text(lesson.from)}`}
              </span>
            </span>
            {lesson.kind !== "judgement" && (
              <Badge tone={lesson.scope === "private" ? "vault" : "estimate"}>
                {lesson.scope === "private" ? "keep private" : text(lesson.scope)}
              </Badge>
            )}
          </label>
        ))}
      </div>
      <div className="row">
        <span className="small">
          {selected.filter(Boolean).length} of {lessons.length} selected
        </span>
        <span className="h-right">
          <button
            className="btn btn-sm btn-primary"
            type="button"
            aria-label="Save selected lessons"
            onClick={() =>
              send("lessons.save", {
                lessons: lessons.filter((lesson, i) => selected[i] && lesson.kind !== "judgement"),
              })
            }
          >
            Save to my agent
          </button>
        </span>
      </div>
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
