// SPDX-License-Identifier: Apache-2.0
import { useEffect, useState } from "react";
import { rows, str, type ViewProps } from "./shared";

function converted(at: string, tz: string, viewer: string) {
  const date = new Date(at);
  if (!Number.isFinite(date.getTime())) return null;
  try {
    const day = (zone: string) =>
      new Intl.DateTimeFormat("en-CA", {
        timeZone: zone,
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
      }).format(date);
    const local = day(tz);
    const own = day(viewer);
    return {
      time: new Intl.DateTimeFormat("en-GB", {
        timeZone: tz,
        hour: "2-digit",
        minute: "2-digit",
        timeZoneName: "short",
      }).format(date),
      day: local > own ? "tomorrow" : local < own ? "yesterday" : "",
    };
  } catch {
    return null;
  }
}

export function Zone({ p, send }: Pick<ViewProps, "p" | "send">) {
  const initial = str(p.value, "UTC");
  const [value, setValue] = useState(initial);
  useEffect(() => setValue(initial), [initial]);
  return (
    <div className="col">
      <label className="f01-field">
        <span className="lbl">Time zone</span>
        <select
          className="f01-input"
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            send("tz.change", { value: e.target.value });
          }}
        >
          {[...new Set([initial, ...rows(p.others).map((o) => str(o.tz))])].map((tz) => (
            <option key={tz} value={tz}>
              {tz === initial ? str(p.label, tz) : tz}
            </option>
          ))}
        </select>
      </label>
      <dl className="kv">
        {rows(p.others).map((o) => {
          const local = converted(str(p.at), str(o.tz), value);
          return (
            <div className="f01-pair" key={str(o.participant)}>
              <dt>{str(o.participant)}</dt>
              <dd className="mono">
                {local?.time ?? str(o.tz)}
                {local?.day && (
                  <>
                    {" "}
                    <span className="small">{local.day}</span>
                  </>
                )}
              </dd>
            </div>
          );
        })}
      </dl>
    </div>
  );
}
