// SPDX-License-Identifier: Apache-2.0
import { useId, useState } from "react";
import { Action, Frame, list, Meter, num, obj, type Props, rows, str } from "../f05/shared";
import "../../styles/f07.css";

const clock = (value: unknown) => {
  const raw = str(value);
  const match = raw.match(/T(\d{2}:\d{2})/);
  return match?.[1] ?? raw;
};

export { IndoorMap, MapView, PlacePicker } from "./maps";

function formatCost(value: number, currency: string) {
  try {
    return new Intl.NumberFormat("en-GB", {
      style: "currency",
      currency,
      maximumFractionDigits: 2,
      minimumFractionDigits: 0,
    }).format(value);
  } catch {
    return `${value} ${currency}`;
  }
}
export function RouteCard({ p }: Props) {
  const progress = num(p.progress);
  const state = progress >= 1 ? "arrived" : progress > 0 ? "moving" : "planned";
  const steps = rows(p.steps);
  const minutes = (value: unknown) => {
    const [hours, minute] = clock(value).split(":").map(Number);
    return (hours ?? 0) * 60 + (minute ?? 0);
  };
  const duration = (minutes(p.eta) - minutes(steps[0]?.time) + 1440) % 1440;
  return (
    <Frame name="RouteCard" state={state} className="card f07-route">
      <div className="row">
        <svg className="ico" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M5 17h14l-1.5-6h-11zM7 17v2M17 17v2M7 11l1.5-4h7l1.5 4" />
        </svg>
        <b>{str(p.mode)}</b>
        <span
          className={`h-right tag ${state === "moving" ? "t-changed" : state === "arrived" ? "t-agreed" : "t-private"}`}
        >
          {state === "moving" ? "Changed" : state === "arrived" ? "Arrived" : "Planned"}
        </span>
      </div>
      <div className="row">
        <time className="answer" dateTime={str(p.eta)}>
          {clock(p.eta)}
        </time>
        <span className="small">
          arrive{Number.isFinite(duration) ? ` · ${duration} min` : ""} · {num(p.distance) / 1000}{" "}
          km
        </span>
      </div>
      <Meter value={progress * 100} label="Route progress" />
      <div className="col f07-route-steps">
        {steps.map((step) => (
          <div className="row small" key={str(step.label)}>
            <span className={`pin f07-step-${str(step.state)}`} />
            <span className={step.state === "next" ? undefined : "f07-route-current"}>
              {step.state === "now" ? <b>{str(step.label)}</b> : str(step.label)} · {str(step.time)}
            </span>
          </div>
        ))}
      </div>
      <div className="row">
        <div className="stack">
          {list(p.participants).map((person, index) => (
            <span className={`av av-xs s${(index % 5) + 1}`} key={str(person)}>
              {str(person).slice(-1)}
            </span>
          ))}
        </div>
        <span className="small">
          {list(p.participants).length} members
          {p.costPerMember != null && Boolean(p.currency) && (
            <> · ≈ {formatCost(num(p.costPerMember), str(p.currency))} each</>
          )}
        </span>
      </div>
    </Frame>
  );
}
export function ArrivalCard({ p }: Props) {
  return (
    <Frame name="ArrivalCard" state="arrived">
      <div className="f07-lens">
        <small>
          ARRIVED · <time dateTime={str(p.arrivedAt)}>{clock(p.arrivedAt)}</time>
        </small>
        <b>You're at {str(p.place)}</b>
        <p>{str(p.next)}</p>
      </div>
      <div className="card">
        {rows(p.others).map((r, i) => (
          <div className="row small" key={str(r.participant)}>
            <span className={`av av-xs s${(i % 5) + 2}`}>{str(r.participant).slice(-1)}</span>
            <span className="f07-arrival-person">
              {str(r.participant)} {str(r.state)}
            </span>
            <time className="h-right st" dateTime={str(r.arrivedAt) || undefined}>
              {r.arrivedAt ? clock(r.arrivedAt) : "approx."}
            </time>
          </div>
        ))}
      </div>
    </Frame>
  );
}
export function LocationShare({ p, send }: Props) {
  const group = useId(),
    [precision, setPrecision] = useState(str(p.precision) || "approximate"),
    [until, setUntil] = useState(str(p.until) || "arrival"),
    [sharing, setSharing] = useState(false);
  return (
    <Frame name="LocationShare" state={sharing ? "sharing" : "off"} className="card f07-location">
      <b>Share where you are</b>
      <small>with: {str(p.audience) || str(obj(p.audience).audience)}</small>
      {[
        ["exact", "Exact, while the task runs"],
        ["approximate", "About 500 m"],
        ["place-only", "Only the place"],
        ["off", "Don't share"],
      ].map(([value, label]) => (
        <label className="row" key={value}>
          <input
            type="radio"
            name={group}
            value={value}
            checked={precision === value}
            onChange={() => setPrecision(value ?? "off")}
          />
          <span>{label}</span>
          {value === "approximate" && <span className="h-right st">default</span>}
        </label>
      ))}
      <label className="col">
        Stop sharing
        <span className="f07-select">
          <select value={until} onChange={(e) => setUntil(e.target.value)}>
            {["task end", "time", "arrival"].map((t) => (
              <option key={t} value={t}>
                {t === "arrival"
                  ? "When the task arrives"
                  : t === "task end"
                    ? "When the task ends"
                    : "At a chosen time"}
              </option>
            ))}
          </select>
          <svg className="ico ico-sm" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M6 9l6 6 6-6" />
          </svg>
        </span>
      </label>
      {sharing ? (
        <Action
          onClick={() => {
            send("location.stop");
            setSharing(false);
          }}
        >
          Stop sharing
        </Action>
      ) : (
        <Action
          onClick={() => {
            send(precision === "off" ? "location.stop" : "location.share", {
              audience: p.audience,
              precision,
              until,
            });
            setSharing(precision !== "off");
          }}
        >
          Share for this task
        </Action>
      )}
    </Frame>
  );
}
export function AgendaList({ p, send }: Props) {
  return (
    <Frame name="AgendaList" className="f07-agenda-list">
      <div title={str(p.day)}>
        {rows(p.items).map((r, i) => (
          <div className="f07-agenda" key={`${str(r.time)}-${str(r.title)}`}>
            <time>{str(r.time)}</time>
            <span className={`pin f07-dot-${str(r.state)}`} />
            <span className="f07-agenda-title">
              {r.state === "agreed" ? (
                <>
                  <b>{str(r.title).split(" · ")[0]}</b>
                  {str(r.title).includes(" · ")
                    ? ` · ${str(r.title).split(" · ").slice(1).join(" · ")}`
                    : ""}
                </>
              ) : (
                str(r.title)
              )}
            </span>
            {(r.state === "agreed" || r.state === "needs-you") && (
              <span className={`tag ${r.state === "agreed" ? "t-agreed" : "t-needs"}`}>
                {r.state === "agreed" ? "Agreed" : "Needs you"}
              </span>
            )}
            {Boolean(r.action) && (
              <button
                type="button"
                className="f07-text-action"
                onClick={() => send("item.action", { item: i, action: r.action })}
              >
                {str(r.action)}
              </button>
            )}
          </div>
        ))}
      </div>
    </Frame>
  );
}
function localTime(now: Date, zone: unknown) {
  try {
    return new Intl.DateTimeFormat("en-GB", {
      timeZone: str(zone),
      hour: "2-digit",
      minute: "2-digit",
    }).format(now);
  } catch {
    return "—";
  }
}
const hourOf = (time: string) => Number(time.slice(0, 2)) + Number(time.slice(3)) / 60;
export function TimeZoneStrip({ p }: Props) {
  const now = new Date(str(p.now));
  const people = rows(p.people);
  const viewerHour = hourOf(localTime(now, people[0]?.tz));
  const working = people.filter((person) => {
    const hour = hourOf(localTime(now, person.tz));
    return rows(person.workingHours).some((range) =>
      num(range.end) < num(range.start)
        ? hour >= num(range.start) || hour < num(range.end)
        : hour >= num(range.start) && hour < num(range.end),
    );
  });
  const names = working.map((person) => str(person.participant)).join(" and ");
  return (
    <Frame name="TimeZoneStrip">
      <div className="f07-hours st">
        <span>00</span>
        <span>06</span>
        <span>12</span>
        <span>18</span>
        <span>24</span>
      </div>
      {people.map((person, index) => {
        const time = localTime(now, person.tz);
        const offset = hourOf(time) - viewerHour;
        const bands = rows(person.workingHours).flatMap((range) => {
          if (!Number.isFinite(offset)) return [];
          const start = (((num(range.start) - offset) % 24) + 24) % 24;
          const hours = num(range.end) - num(range.start);
          const duration = Math.abs(hours) >= 24 ? 24 : ((hours % 24) + 24) % 24;
          const end = start + duration;
          return end > 24
            ? [
                [start, 24],
                [0, end - 24],
              ]
            : [[start, end]];
        });
        return (
          <div className="f07-zone small" key={str(person.participant)}>
            <span className={`av av-xs s${[3, 1, 5][index % 3]}`}>
              {str(person.participant).slice(-1)}
            </span>
            <span className="f07-zone-name">{str(person.participant)}</span>
            <div className="f07-zonebar">
              {bands.map(([start = 0, end = 0]) => (
                <span
                  key={start}
                  style={{
                    left: `${Math.floor((start / 24) * 100)}%`,
                    width: `${end === 24 ? 100 - Math.floor((start / 24) * 100) : Math.round(((end - start) / 24) * 100)}%`,
                  }}
                />
              ))}
              {Number.isFinite(viewerHour) && (
                <i
                  title={localTime(now, people[0]?.tz)}
                  style={{ left: `${Math.round((Math.floor(viewerHour) / 24) * 100)}%` }}
                />
              )}
            </div>
            <time className="num">{time}</time>
          </div>
        );
      })}
      <div className="card card-2 f07-zone-note">
        <span className="small">
          <b>Now:</b>{" "}
          {working.length
            ? `${names} ${working.length === 1 ? "is" : "are"} at work.`
            : "No shared working hours now."}{" "}
          Shared hours come from a PSI over working-hour ranges, on each member's own clock.
        </span>
      </div>
      <div className="row small f07-zone-legend">
        <span className="row">
          <i className="working" />
          working
        </span>
        <span className="row">
          <i className="now" />
          now
        </span>
        <span className="h-right st">local clocks</span>
      </div>
    </Frame>
  );
}
export function CalendarWeek({ p, send }: Props) {
  const range = obj(p.range),
    start = Date.parse(str(range.start)),
    events = rows(p.events);
  const current = str(events.find((event) => event.now)?.now);
  const currentDate = new Date(current);
  return (
    <Frame name="CalendarWeek" className="f07-calendar-view">
      <div className="f07-calendar">
        <div className="f07-time-gutter">
          <span />
          {["09", "11", "13", "15", "17"].map((hour) => (
            <time className="st" key={hour}>
              {hour}
            </time>
          ))}
        </div>
        {Array.from({ length: 5 }, (_, i) => {
          const day = new Date(start + i * 86400000),
            valid = Number.isFinite(day.getTime()),
            key = valid ? day.toISOString().slice(0, 10) : String(i);
          return (
            <div
              className={`f07-day${current.startsWith(key) ? " f07-day-current" : ""}`}
              key={key}
            >
              <small className="st" style={{ fontFamily: '"F05 Sheet Mono", var(--font-mono)' }}>
                {valid
                  ? day.toLocaleDateString("en-GB", {
                      weekday: "short",
                      day: "numeric",
                      timeZone: "UTC",
                    })
                  : "—"}
              </small>
              <div>
                {events
                  .filter((e) => str(e.start).slice(0, 10) === key)
                  .map((e) => {
                    const date = new Date(str(e.start)),
                      end = new Date(str(e.end)),
                      top = Math.max(0, (date.getUTCHours() - 9 + date.getUTCMinutes() / 60) * 17),
                      height = Math.max(22, ((end.getTime() - date.getTime()) / 3600000) * 17);
                    return (
                      <button
                        type="button"
                        key={`${str(e.start)}-${str(e.task ?? e.kind)}`}
                        className={`f07-event ${str(e.kind)} ${str(e.state)}`}
                        style={{ top, height }}
                        title={`${str(e.start)} – ${str(e.end)}`}
                        disabled={e.kind === "private-busy"}
                        onClick={() => send("event.open", { event: e })}
                      >
                        {e.kind === "private-busy" ? "busy" : str(e.task ?? e.label ?? e.kind)}
                      </button>
                    );
                  })}
                {current.startsWith(key) && Number.isFinite(currentDate.getTime()) && (
                  <span
                    className="f07-calendar-now"
                    style={{
                      top: (currentDate.getUTCHours() - 9 + currentDate.getUTCMinutes() / 60) * 17,
                    }}
                  />
                )}
              </div>
            </div>
          );
        })}
      </div>
      <div className="row small f07-calendar-legend">
        <span className="row">
          <i className="f07-busy-swatch" />
          your private busy (only you see the label)
        </span>
        <span className="row">
          <i className="f07-now-swatch" />
          now
        </span>
        <button
          type="button"
          className="f07-text-action h-right"
          onClick={() => send("calendar.export", { range: p.range })}
        >
          Export .ics
        </button>
      </div>
    </Frame>
  );
}
