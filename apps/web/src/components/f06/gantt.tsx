// SPDX-License-Identifier: Apache-2.0
import { Frame, list, obj, type Props, rows, str } from "../f05/shared";
import { Timeline } from "./work";

const day = 86_400_000;
const date = (value: unknown) => Date.parse(str(value));
const dayLabel = (value: number) =>
  new Date(value).toLocaleDateString("en-GB", {
    weekday: "short",
    day: "numeric",
    timeZone: "UTC",
  });
function schedule(data: Record<string, unknown>[]) {
  const starts = data.map((r) => date(r.start)).filter(Number.isFinite);
  const ends = data.map((r) => date(r.end)).filter(Number.isFinite);
  // Compress dates without a task boundary, as on the schedule sheet.
  const days = [...new Set([...starts, ...ends].map((t) => Math.floor(t / day) * day))].sort(
    (a, b) => a - b,
  );
  const position = (value: unknown) => {
    const t = date(value),
      midnight = Math.floor(t / day) * day;
    if (days.length && t < (days[0] ?? 0)) return 0;
    if (days.length && t >= (days.at(-1) ?? 0) + day) return 100;
    const index = days.findLastIndex((d) => d <= midnight);
    return Number.isFinite(t)
      ? Math.max(
          0,
          Math.min(
            100,
            (100 * (Math.max(0, index) + (t - midnight) / day)) / Math.max(1, days.length),
          ),
        )
      : 0;
  };
  return { days, position };
}
function ScheduleLegend({ p }: Pick<Props, "p">) {
  return (
    <div className="row small f06-gantt-legend">
      <span className="row">
        <i className="f06-key-active" />
        in progress
      </span>
      <span className="row">
        <i className="f06-key-now" />
        now
      </span>
      {list(p.deadlines).map((d) => (
        <span className="row" key={str(d)}>
          <i className="f06-key-deadline" />
          goal deadline {str(d)}
        </span>
      ))}
      <span>bar colour = assignee seat</span>
      <span className="h-right blue">
        Critical path: {list(p.criticalPath).map(str).join(" → ")}
      </span>
    </div>
  );
}
export function Gantt({ p, send }: Props) {
  const data = rows(p.rows),
    { days, position } = schedule(data);
  const now = date(p.now);
  return (
    <Frame name="Gantt" className="f06-schedule">
      <div className="f06-gantt">
        <div
          className="f06-axis"
          style={{ gridTemplateColumns: `170px repeat(${Math.max(1, days.length)},1fr)` }}
        >
          <span />
          {days.map((t) => (
            <span
              key={t}
              className={`st ${Math.floor(now / day) === Math.floor(t / day) ? "blue" : ""}`}
            >
              {dayLabel(t)}
              {Math.floor(now / day) === Math.floor(t / day) ? " · today" : ""}
            </span>
          ))}
        </div>
        <div className="f06-gantt-rows">
          {Number.isFinite(now) && (
            <span
              className="f06-schedule-now"
              style={{ left: `calc(170px + (100% - 170px) * ${position(p.now) / 100})` }}
            />
          )}
          {list(p.deadlines).map((d, i) => (
            <span
              key={str(d) || i}
              className="f06-deadline"
              style={{ left: `calc(170px + (100% - 170px) * ${position(obj(d).at ?? d) / 100})` }}
            />
          ))}
          {data.map((r) => {
            const active = date(r.start) <= now && now < date(r.end) && r.status !== "done";
            const seat = str(r.assignee).endsWith("B") ? "teal" : "muted";
            return (
              <div className="f06-gantt-row" key={str(r.task)}>
                <span className="row small">
                  <span className="mono st">{str(r.task)}</span>
                  {str(r.title)}
                </span>
                <div className="f06-gantt-track">
                  <button
                    type="button"
                    aria-label={`${str(r.assignee)} · ${str(r.status)}`}
                    className={`f06-taskbar ${active ? "active" : r.status === "done" ? "done" : seat}`}
                    style={{
                      left: `${position(r.start)}%`,
                      width: `${Math.max(1, position(r.end) - position(r.start))}%`,
                    }}
                    onClick={() => send("task.open", { id: r.task })}
                  >
                    {str(r.assignee).slice(-1)}
                    {r.note
                      ? ` · ${str(r.note)}`
                      : active
                        ? " · now"
                        : r.status === "done"
                          ? " · done"
                          : ""}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
        <ScheduleLegend p={p} />
      </div>
      <div className="f06-schedule-compact">
        <Timeline
          items={data.map((r) => ({
            when: Number.isFinite(date(r.start))
              ? `${dayLabel(date(r.start))} · ${new Date(date(r.start)).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: "UTC" })}`
              : str(r.start),
            title: str(r.title) || str(r.task),
            assignee: str(r.assignee),
            state:
              r.status === "done"
                ? "done"
                : date(r.start) <= now && now < date(r.end)
                  ? "now"
                  : "next",
          }))}
        />
      </div>
    </Frame>
  );
}
