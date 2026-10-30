// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { Badge, type BadgeKind } from "./primitives";
import { number, rows, shown, str, type ViewProps } from "./shared";

export function DataDisplay({ name, p, send }: ViewProps) {
  if (name === "KeyValue")
    return (
      <dl className="kv">
        {rows(p.pairs).map((r) => (
          <div className="f01-pair" key={str(r.label)}>
            <dt>{str(r.label)}</dt>
            <dd>
              {shown(r.value)}
              {typeof r.provenance === "string" && (
                <>
                  {" "}
                  <Badge kind={r.provenance as BadgeKind} label={r.provenance} />
                </>
              )}
            </dd>
          </div>
        ))}
      </dl>
    );
  if (name === "Table")
    return (
      <div className="f01-table-scroll">
        <table className="f01-table">
          <thead>
            <tr>
              {rows(p.columns).map((c) => (
                <th key={str(c.key)}>
                  {p.sortable ? (
                    <button type="button" onClick={() => send("sort", { key: c.key })}>
                      {str(c.label)} ↕
                    </button>
                  ) : (
                    str(c.label)
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows(p.rows).map((r, index) => (
              <tr key={str(r.id, String(index))}>
                {rows(p.columns).map((c, i) => (
                  <td
                    key={str(c.key)}
                    style={{ textAlign: c.align === "right" ? "right" : "left" }}
                  >
                    {i === 0 ? (
                      <button type="button" onClick={() => send("open", { row: r })}>
                        {shown(r[str(c.key)])}
                      </button>
                    ) : (
                      shown(r[str(c.key)])
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {!rows(p.rows).length && <span className="small">No rows</span>}
      </div>
    );
  const items = rows(p.items).slice(0, number(p.max, 50));
  return (
    <div className="f01-list">
      {items.length ? (
        items.map((r, index) => (
          <div key={str(r.id, String(index))} className="head">
            {!!p.selectable && (
              <input
                type="checkbox"
                aria-label={`Select ${str(r.title)}`}
                onChange={() => send("select", { item: r })}
              />
            )}
            <button type="button" onClick={() => send("open", { item: r })}>
              <b>{str(r.title, str(r.label))}</b>
              <span className="small">{str(r.meta)}</span>
            </button>
            <span className="small">{str(r.trailing)}</span>
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
  return (
    <div className={`f01-gauge f01-tone-${str(band?.tone, "ok")}`}>
      <div className="head">
        <span>{str(p.label)}</span>
        <span className="h-right mono">
          {value} {str(p.unit)}
        </span>
      </div>
      {name === "Meter" ? (
        <meter aria-label={str(p.label)} min={min} max={max} value={value} />
      ) : (
        <div
          role="progressbar"
          aria-label={str(p.label)}
          aria-valuemin={min}
          aria-valuemax={max}
          aria-valuenow={value}
          className="f01-bar"
        >
          <span style={{ width: `${percent}%` }} />
        </div>
      )}
      {number(p.steps) > 0 && (
        <span className="small">
          {Math.round((percent / 100) * number(p.steps))} of {number(p.steps)}
        </span>
      )}
    </div>
  );
}

export function Slots({ p, send }: ViewProps) {
  const [selected, setSelected] = useState(str(p.selected));
  return (
    <div className="f01-slots">
      {rows(p.days).map((day) => (
        <div className="col" key={str(day.date)}>
          <b>{str(day.date)}</b>
          {rows(day.slots).map((slot) => (
            <button
              type="button"
              className={`f01-slot f01-slot-${str(slot.state)}`}
              key={str(slot.start)}
              disabled={slot.state === "off"}
              aria-pressed={selected === slot.start}
              onClick={() => {
                send(selected === slot.start ? "slot.release" : "slot.hold", { start: slot.start });
                setSelected(selected === slot.start ? "" : str(slot.start));
              }}
            >
              {str(slot.start).slice(-5)}
            </button>
          ))}
        </div>
      ))}
      {!rows(p.days).length && <span className="small">No shared times</span>}
      <span className="small">
        {number(p.duration, 30)} min · {str(p.source)}
      </span>
    </div>
  );
}

export function Time({ name, p, send }: ViewProps) {
  if (name === "TimeZone")
    return (
      <div className="col">
        <label>
          Time zone{" "}
          <select
            className="f01-input"
            defaultValue={str(p.value, "UTC")}
            onChange={(e) => send("tz.change", { value: e.target.value })}
          >
            {[...new Set([str(p.value, "UTC"), ...rows(p.others).map((o) => str(o.tz))])].map(
              (tz) => (
                <option key={tz}>{tz}</option>
              ),
            )}
          </select>
        </label>
        {rows(p.others).map((o) => (
          <span className="small" key={str(o.participant)}>
            {str(o.participant)} · {str(o.tz)}
          </span>
        ))}
      </div>
    );
  const left = new Date(str(p.deadline)).getTime() - Date.now();
  return (
    <div className={`f01-deadline ${left < 0 ? "f01-error" : left < 3600000 ? "f01-warning" : ""}`}>
      <b>{str(p.label)}</b>
      <time dateTime={str(p.deadline)}>{str(p.deadline)}</time>
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
