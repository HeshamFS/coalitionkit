// SPDX-License-Identifier: Apache-2.0
import { useEffect, useState } from "react";
import { Glyph } from "./Glyph";
import { Avatar, Badge, type BadgeKind, ScopeBadge, type Seat } from "./primitives";
import { number, obj, rows, shown, str, type ViewProps } from "./shared";
import { TableView } from "./TableView";
import { shortTime } from "./time";
import { Zone } from "./Zone";

export function DataDisplay({ name, p, send, build }: ViewProps) {
  if (name === "KeyValue")
    return (
      <dl className="kv">
        {rows(p.pairs).map((r) => (
          <div className="f01-pair" key={str(r.label)}>
            <dt>{str(r.label)}</dt>
            <dd className={r.format === "mono" ? "f01-kv-mono" : undefined}>
              {shown(r.value)}
              {typeof r.provenance === "string" && (
                <>
                  {" "}
                  <Badge kind={r.provenance as BadgeKind} label={r.provenance} />
                </>
              )}
              {r.scope ? (
                <>
                  {" "}
                  <ScopeBadge audience={str(r.scope)} />
                </>
              ) : null}
            </dd>
          </div>
        ))}
      </dl>
    );
  if (name === "Table") return <TableView p={p} send={send} />;
  const items = rows(p.items).slice(0, Math.max(0, number(p.max, 50)));
  return (
    <div className="f01-list">
      {items.length ? (
        items.map((r, index) => (
          <div key={str(r.id, String(index))} className="head">
            {r.leading ? (
              <Avatar
                label={str(obj(r.leading).label, str(r.title))}
                seat={(obj(r.leading).seat ?? "host") as Seat}
              />
            ) : null}
            {!!p.selectable && (
              <input
                type="checkbox"
                aria-label={`Select ${str(r.title)}`}
                onChange={() => send("select", { item: r })}
              />
            )}
            {p.template ? (
              build(str(p.template))
            ) : (
              <button type="button" onClick={() => send("open", { item: r })}>
                <b>{str(r.title, str(r.label))}</b>
                <span className="small">{str(r.meta)}</span>
              </button>
            )}
            {r.trailing === "live" ? (
              <span className="live-dot" role="img" aria-label="Live" />
            ) : (
              <span className="st">{str(r.trailing)}</span>
            )}
          </div>
        ))
      ) : (
        <span className="small">{str(p.empty, "No items yet")}</span>
      )}
    </div>
  );
}

export function Gauge({ name, p }: ViewProps) {
  const value = number(p.value);
  const min = number(p.min);
  const max = number(p.max, 100);
  const percent = Math.max(0, Math.min(100, ((value - min) / Math.max(1, max - min)) * 100));
  const band = rows(p.bands).find((b) => value <= number(b.upTo));
  const steps = Math.max(0, Math.min(20, Math.round(number(p.steps))));
  const complete = Math.round((percent / 100) * steps);
  const provenance = p.provenance ? (
    <Badge kind={p.provenance as BadgeKind} label={str(p.provenance)} />
  ) : null;
  if (Array.isArray(p.stepLabels))
    return (
      <ol className="f01-steps" aria-label={str(p.label)}>
        {p.stepLabels.map((label, index) => (
          <li
            key={str(label)}
            className={index + 1 < value ? "is-done" : index + 1 === value ? "is-current" : ""}
            aria-current={index + 1 === value ? "step" : undefined}
          >
            <i>{index + 1 < value ? "✓" : index + 1}</i>
            {str(label)}
          </li>
        ))}
      </ol>
    );
  if (name === "Meter")
    return (
      <div className={`row f01-gauge f01-meter f01-tone-${str(band?.tone, "ok")}`}>
        <meter
          className="sr-only"
          aria-label={`${str(p.label)} ${str(p.unit)}`}
          value={value}
          min={min}
          max={max}
        />
        <svg className="ring" viewBox="0 0 44 44" aria-hidden="true">
          <circle cx="22" cy="22" r="18" fill="none" stroke="var(--surface-3)" strokeWidth="5" />
          <circle
            cx="22"
            cy="22"
            r="18"
            fill="none"
            stroke="var(--gauge-color)"
            strokeWidth="5"
            strokeDasharray="113.097"
            strokeDashoffset={113.097 * (1 - percent / 100)}
            strokeLinecap="round"
            transform="rotate(-90 22 22)"
          />
          <text
            x="22"
            y="26"
            textAnchor="middle"
            fontFamily="var(--font-mono)"
            fontSize="11"
            fill="var(--ink)"
          >
            {value}
          </text>
        </svg>
        <div className="col" style={{ gap: 0 }}>
          <span className="lbl">{str(p.label)}</span>
          {p.caption ? <span className="small">{str(p.caption)}</span> : null}
          {provenance}
        </div>
      </div>
    );
  return (
    <div className="f01-gauge">
      <div className="head">
        <span className="lbl">{str(p.label)}</span>
        <span className="h-right mono small">
          {steps ? `${complete} of ${steps}` : `${value} ${str(p.unit)}`}
        </span>
      </div>
      <div
        role="progressbar"
        aria-label={str(p.label)}
        aria-valuemin={min}
        aria-valuemax={max}
        aria-valuenow={value}
        className={steps ? "f01-segments" : "f01-bar"}
      >
        {steps ? (
          Array.from({ length: steps }, (_, index) => index + 1).map((step) => (
            <div className="f01-bar" key={step}>
              <span style={{ width: step <= complete ? "100%" : "0%" }} />
            </div>
          ))
        ) : (
          <span style={{ width: `${percent}%` }} />
        )}
      </div>
      {provenance}
    </div>
  );
}

export function Slots({ p, send }: ViewProps) {
  const [selected, setSelected] = useState(str(p.selected));
  useEffect(() => setSelected(str(p.selected)), [p.selected]);
  const days = rows(p.days);
  return (
    <div className="col">
      <div
        className="f01-slot-days"
        style={{
          gridTemplateColumns: `repeat(${Math.max(1, Math.min(7, days.length))}, minmax(0, 1fr))`,
        }}
      >
        {days.map((day) => (
          <div className="col" key={str(day.date)}>
            <span className="lbl">{str(day.date)}</span>
            {rows(day.slots).map((slot) => (
              <button
                type="button"
                className={`f01-slot f01-slot-${str(slot.state)}`}
                key={str(slot.start)}
                disabled={slot.state === "off"}
                aria-pressed={selected === slot.start}
                onClick={() => {
                  send(selected === slot.start ? "slot.release" : "slot.hold", {
                    start: slot.start,
                  });
                  setSelected(selected === slot.start ? "" : str(slot.start));
                }}
              >
                {shortTime(str(slot.start))}
              </button>
            ))}
          </div>
        ))}
      </div>
      {!days.length && <span className="small">No shared times</span>}
      <div className="row wrap f01-slot-legend">
        <span className="row small">
          <i className="f01-slot f01-slot-shared" />
          {p.participants ? `free for all ${number(p.participants)} members` : "free for everyone"}
        </span>
        <span className="row small">
          <i className="f01-slot" />
          free for you
        </span>
        <span className="row small">
          <i className="f01-slot f01-slot-off" />
          not free (nobody learns why)
        </span>
        {p.participants && selected ? (
          <button
            type="button"
            className="btn btn-sm btn-primary f01-slot-hold"
            onClick={() => send("slot.hold", { start: selected })}
          >
            Hold {new Intl.DateTimeFormat("en-GB", { weekday: "short" }).format(new Date(selected))}{" "}
            {shortTime(selected)} for {number(p.participants)}
          </button>
        ) : null}
      </div>
      <span className="sr-only">
        {number(p.duration, 30)} min ·{" "}
        {p.source === "psi_match" ? "Private calendar match" : str(p.source)}
      </span>
    </div>
  );
}

export function Time({ name, p, send }: ViewProps) {
  const [now, setNow] = useState(Date.now);
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  if (name === "TimeZone") return <Zone p={p} send={send} />;
  const deadline = str(p.deadline);
  const left = new Date(deadline).getTime() - now;
  const seconds = Math.max(0, Math.ceil(left / 1000));
  const remaining =
    left <= 0
      ? "Passed"
      : left > 3600000
        ? `${Math.floor(seconds / 3600)} h ${Math.floor((seconds % 3600) / 60)} m`
        : `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
  return (
    <div className={`f01-deadline ${left < 0 ? "f01-error" : left < 3600000 ? "f01-warning" : ""}`}>
      <div className="head">
        <Glyph name="clock" />
        <b>{str(p.label)}</b>
        {Number.isFinite(left) && <span className="h-right mono">{remaining}</span>}
      </div>
      {!!p.startedAt && Number.isFinite(left) && (
        <div
          className="f01-bar"
          role="progressbar"
          aria-label="Decision window elapsed"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={elapsed(str(p.startedAt), deadline, now)}
        >
          <span
            style={{
              width: `${elapsed(str(p.startedAt), deadline, now)}%`,
              background: "currentColor",
            }}
          />
        </div>
      )}
      <time className="sr-only" dateTime={deadline} title={deadline}>
        {deadline}
      </time>
      <span className="small">{str(p.consequence)}</span>
    </div>
  );
}

/** A deliberately small markdown vocabulary; raw HTML always stays text. */
export function Rich({ p, send }: ViewProps) {
  const text = str(p.markdown);
  const allow = str(p.allow);
  const pattern =
    allow === "bold"
      ? /(\*\*[^*]+\*\*)/g
      : allow === "italic"
        ? /(\*[^*]+\*)/g
        : allow === "link"
          ? /(\[[^\]]+\]\(https:\/\/[^)]+\))/g
          : /($^)/g;
  if (allow === "list")
    return (
      <ul>
        {text.split("\n").map((line, i) => (
          // biome-ignore lint/suspicious/noArrayIndexKey: immutable markdown tokens
          <li key={`${i}-${line}`}>{line.replace(/^[-*] /, "")}</li>
        ))}
      </ul>
    );
  return (
    <span>
      {text.split(pattern).map((part, i) => {
        const key = `${i}-${part}`;
        if (allow === "bold" && part.startsWith("**"))
          return <strong key={key}>{part.slice(2, -2)}</strong>;
        if (allow === "italic" && part.startsWith("*"))
          return <em key={key}>{part.slice(1, -1)}</em>;
        const link = /^\[([^\]]+)\]\((https:\/\/[^)]+)\)$/.exec(part);
        if (link)
          return (
            <a
              key={key}
              href={link[2]}
              onClick={(e) => {
                e.preventDefault();
                send("link.open", { href: link[2] });
              }}
            >
              {link[1]}
            </a>
          );
        return <span key={key}>{part}</span>;
      })}
    </span>
  );
}

function elapsed(start: string, end: string, now: number) {
  const from = new Date(start).getTime();
  const duration = new Date(end).getTime() - from;
  return duration > 0 ? Math.min(100, Math.max(0, Math.round(((now - from) / duration) * 100))) : 0;
}
