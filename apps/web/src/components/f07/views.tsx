// SPDX-License-Identifier: Apache-2.0
import { useId, useState } from "react";
import { Action, Frame, list, Mark, Meter, num, obj, type Props, rows, str } from "../f05/shared";
import "../../styles/f07.css";

export { IndoorMap, MapView, PlacePicker } from "./maps";
export function RouteCard({ p }: Props) {
  const progress = num(p.progress),
    state = progress >= 1 ? "arrived" : progress > 0 ? "moving" : "planned";
  return (
    <Frame name="RouteCard" state={state} className="card">
      <div className="row sp">
        <b>{str(p.mode)}</b>
        <Mark state={state} />
      </div>
      <div className="row">
        <b className="f07-arrival">{str(p.eta)}</b>
        <span>{num(p.distance) / 1000} km</span>
      </div>
      <Meter value={progress * 100} label="Route progress" />
      {rows(p.steps).map((r) => (
        <div className="row" key={str(r.label)}>
          <Mark state={r.state} />
          <span>
            {str(r.label)} · {str(r.time)}
          </span>
        </div>
      ))}
      <small>With {list(p.participants).map(str).join(", ")}</small>
    </Frame>
  );
}
export function ArrivalCard({ p }: Props) {
  return (
    <Frame name="ArrivalCard" state="arrived">
      <div className="f07-lens">
        <small>ARRIVED · {str(p.arrivedAt)}</small>
        <b>You're at {str(p.place)}</b>
        <p>{str(p.next)}</p>
      </div>
      <div className="card">
        {rows(p.others).map((r) => (
          <div className="row sp" key={str(r.participant)}>
            <span>{str(r.participant)}</span>
            <small>{str(r.state)}</small>
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
    <Frame name="LocationShare" state={sharing ? "sharing" : "off"} className="card">
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
          {label}
        </label>
      ))}
      <label className="col">
        Stop sharing
        <select value={until} onChange={(e) => setUntil(e.target.value)}>
          {["task end", "time", "arrival"].map((t) => (
            <option key={t}>{t}</option>
          ))}
        </select>
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
    <Frame name="AgendaList">
      <small>{str(p.day)}</small>
      {rows(p.items).map((r, i) => (
        <div className="f07-agenda" key={`${str(r.time)}-${str(r.title)}`}>
          <time>{str(r.time)}</time>
          <span>{str(r.title)}</span>
          <Mark state={r.state} />
          {Boolean(r.action) && (
            <Action onClick={() => send("item.action", { item: i, action: r.action })}>
              {str(r.action)}
            </Action>
          )}
        </div>
      ))}
    </Frame>
  );
}
export function TimeZoneStrip({ p }: Props) {
  const now = new Date(str(p.now));
  return (
    <Frame name="TimeZoneStrip">
      <div className="f07-hours">
        <span>00</span>
        <span>06</span>
        <span>12</span>
        <span>18</span>
        <span>24</span>
      </div>
      {rows(p.people).map((r) => {
        let time = "—";
        try {
          time = new Intl.DateTimeFormat("en-GB", {
            timeZone: str(r.tz),
            hour: "2-digit",
            minute: "2-digit",
          }).format(now);
        } catch {}
        const hour = Number(time.slice(0, 2)) + Number(time.slice(3)) / 60;
        return (
          <div className="f07-zone" key={str(r.participant)}>
            <span>{str(r.participant)}</span>
            <div className="f07-zonebar">
              {rows(r.workingHours).map((h) => (
                <span
                  key={str(h.start)}
                  style={{
                    left: `${(num(h.start) / 24) * 100}%`,
                    width: `${((num(h.end) - num(h.start)) / 24) * 100}%`,
                  }}
                />
              ))}
              {Number.isFinite(hour) && <i style={{ left: `${(hour / 24) * 100}%` }} />}
            </div>
            <time>{time}</time>
          </div>
        );
      })}
      <small>Working ranges · local clocks · now</small>
    </Frame>
  );
}
export function CalendarWeek({ p, send }: Props) {
  const range = obj(p.range),
    start = Date.parse(str(range.start)),
    events = rows(p.events);
  return (
    <Frame name="CalendarWeek">
      <div className="f07-calendar">
        {Array.from({ length: 5 }, (_, i) => {
          const day = new Date(start + i * 86400000),
            valid = Number.isFinite(day.getTime()),
            key = valid ? day.toISOString().slice(0, 10) : String(i);
          return (
            <div className="f07-day" key={key}>
              <small>
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
                        className={`f07-event ${str(e.kind)}`}
                        style={{ top, height }}
                        disabled={e.kind === "private-busy"}
                        onClick={() => send("event.open", { event: e })}
                      >
                        {e.kind === "private-busy" ? "busy" : str(e.task ?? e.label ?? e.kind)}
                      </button>
                    );
                  })}
              </div>
            </div>
          );
        })}
      </div>
      <div className="row sp">
        <small>Your private busy · only you see the label</small>
        <Action onClick={() => send("calendar.export", { range: p.range })}>Export .ics</Action>
      </div>
    </Frame>
  );
}
