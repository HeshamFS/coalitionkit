// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { Badge, obj, type Props, rows, type Send, text } from "../f08/shared";
import "../../styles/f11.css";

export function Channels({ p, send }: { p: Props; send: Send }) {
  const quiet = obj(p.quiet),
    channels = rows(p.channels);
  const [from, setFrom] = useState(text(quiet.from)),
    [to, setTo] = useState(text(quiet.to));
  const [editing, setEditing] = useState(false);
  const [levels, setLevels] = useState(channels.map((c) => text(c.level)));
  const update = (i: number, level: string) => {
    setLevels((old) => old.map((v, j) => (i === j ? level : v)));
    send("channel.set", { kind: channels[i]?.kind, level });
  };
  return (
    <>
      <b className="f11-control-title">How to reach you</b>
      <div className="f11-channels">
        {channels.map((c, i) => (
          <div className="row" key={text(c.kind)}>
            <span className="small grow">{text(c.label ?? c.kind)}</span>
            <select
              aria-label={text(c.kind)}
              className="f11-channel-level"
              value={levels[i]}
              onChange={(e) => update(i, e.target.value)}
            >
              {["everything", "needs-you", "next-step", "digest", "off"].map((level) => (
                <option key={level} value={level}>
                  {level === "needs-you"
                    ? "needs you"
                    : level === "next-step"
                      ? "next step only"
                      : level === "digest"
                        ? "daily 08:00"
                        : level === "off"
                          ? text(c.offLabel ?? "off")
                          : level}
                </option>
              ))}
            </select>
            <button
              type="button"
              className={`switch ${levels[i] === "off" ? "switch-off" : ""}`}
              aria-label={`Enable ${text(c.label ?? c.kind)}`}
              aria-pressed={levels[i] !== "off"}
              onClick={() =>
                update(i, levels[i] === "off" ? text(c.enabledLevel ?? "needs-you") : "off")
              }
            />
          </div>
        ))}
      </div>
      <div className="row f11-quiet-row">
        <span className="lbl">Quiet</span>
        <button
          type="button"
          className="btn btn-sm"
          aria-label="Save quiet hours"
          onClick={() => {
            send("quiet.set", { from, to, tz: quiet.tz });
            setEditing(!editing);
          }}
        >
          {from} – {to}
          <svg className="ico ico-sm" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M6 9l6 6 6-6" />
          </svg>
        </button>
        <span className="small">deadlines inside quiet hours warn you earlier</span>
      </div>
      {editing && (
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
          <button
            type="button"
            className="btn btn-sm"
            onClick={() => {
              send("quiet.set", { from, to, tz: quiet.tz });
              setEditing(false);
            }}
          >
            Save
          </button>
        </fieldset>
      )}
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
      <span className="st">{p.value === undefined ? "Not run yet" : text(p.context)}</span>
    </div>
  );
}
