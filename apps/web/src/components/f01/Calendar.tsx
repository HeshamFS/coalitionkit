// SPDX-License-Identifier: Apache-2.0
import { useEffect, useId, useRef, useState } from "react";
import { Glyph } from "./Glyph";
import { str, type ViewProps } from "./shared";

const dateKey = (date: Date) =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
const parse = (value: string) => new Date(`${value.slice(0, 10)}T12:00:00`);
const dates = (value: unknown) =>
  Array.isArray(value)
    ? value.map((v) => str(v).slice(0, 10)).filter((v) => Number.isFinite(parse(v).getTime()))
    : [];
const short = (value: string) =>
  new Intl.DateTimeFormat("en-GB", { weekday: "short", day: "numeric" }).format(parse(value));

export function Calendar({ p, send }: ViewProps) {
  const [value, setValue] = useState(dates(p.value));
  const [month, setMonth] = useState(() => (value[0] ? parse(value[0]) : new Date()));
  const [open, setOpen] = useState(false);
  const [pickingEnd, setPickingEnd] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const id = useId();
  useEffect(() => {
    const next = dates(p.value);
    setValue(next);
    if (next[0]) setMonth(parse(next[0]));
    setPickingEnd(false);
  }, [p.value]);
  useEffect(() => {
    const close = (e: PointerEvent) => {
      if (!root.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, []);
  const choose = (date: string) => {
    const next = pickingEnd && value[0] ? [value[0], date].sort() : [date];
    setValue(next);
    setPickingEnd(!pickingEnd);
    if (next.length === 2) {
      send("change", { value: next });
      setOpen(false);
      trigger.current?.focus();
    }
  };
  return (
    <div className="f01-calendar" ref={root}>
      <button
        ref={trigger}
        type="button"
        className={`f01-calendar-trigger${open ? " is-open" : ""}`}
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen(!open)}
      >
        <Glyph name="calendar" size="sm" />
        {value.length
          ? `${value.map(short).join(" – ")} ${new Intl.DateTimeFormat("en-GB", { month: "short" }).format(parse(value.at(-1) ?? ""))}`
          : "Choose dates"}
        <Glyph name="down" size="sm" />
      </button>
      {open && (
        <div
          id={id}
          role="dialog"
          aria-label="Choose date range"
          className="f01-calendar-popup"
          onKeyDown={(e) => {
            if (e.key === "Escape") {
              setOpen(false);
              trigger.current?.focus();
            }
          }}
        >
          <div className="row sp">
            <b>{new Intl.DateTimeFormat("en-GB", { month: "long" }).format(month)}</b>
            <div className="row">
              <button
                className="icon-btn"
                type="button"
                aria-label="Previous month"
                onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))}
              >
                ‹
              </button>
              <button
                className="icon-btn"
                type="button"
                aria-label="Next month"
                onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))}
              >
                ›
              </button>
            </div>
          </div>
          <CalendarDays
            month={month}
            value={value}
            busy={dates(p.busy)}
            min={str(p.min)}
            max={str(p.max)}
            choose={choose}
          />
          <div className="row f01-calendar-legend">
            <span className="row st">
              <i className="pin" />
              chosen
            </span>
            <span className="row st">
              <i className="pin" />
              someone busy
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

function CalendarDays({
  month,
  value,
  busy,
  min,
  max,
  choose,
}: {
  month: Date;
  value: string[];
  busy: string[];
  min: string;
  max: string;
  choose: (date: string) => void;
}) {
  const first = new Date(month.getFullYear(), month.getMonth(), 1);
  const offset = (first.getDay() + 6) % 7;
  const count = new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate();
  const days = Array.from(
    { length: Math.ceil((offset + count) / 7) * 7 },
    (_, i) => new Date(month.getFullYear(), month.getMonth(), i - offset + 1),
  );
  const today = dateKey(new Date());
  return (
    <div className="f01-calendar-days">
      {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((day) => (
        <span className="st" key={day} title={day}>
          {day[0]}
        </span>
      ))}
      {days.map((day) => {
        const key = dateKey(day);
        const unavailable =
          busy.includes(key) ||
          (!!min && key < min.slice(0, 10)) ||
          (!!max && key > max.slice(0, 10));
        return (
          <button
            type="button"
            key={key}
            disabled={unavailable}
            aria-label={key}
            aria-pressed={value.includes(key)}
            aria-current={key === today ? "date" : undefined}
            data-outside={day.getMonth() !== month.getMonth()}
            data-busy={busy.includes(key)}
            data-between={!!value[0] && !!value[1] && key > value[0] && key < value[1]}
            onClick={() => choose(key)}
          >
            {day.getDate()}
          </button>
        );
      })}
    </div>
  );
}
