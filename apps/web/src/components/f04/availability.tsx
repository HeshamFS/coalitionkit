// SPDX-License-Identifier: Apache-2.0
import { Fragment, useRef, useState } from "react";
import { type Data, Frame, label, list, text, type View } from "../f02/ui";

export function AvailabilityGrid({ p, send }: View) {
  const days = list(p.days);
  const slots = list(p.slots);
  const times = [...new Set(slots.map(label))];
  const [selected, set] = useState(
    () => new Set(slots.filter((s) => s.available).map((s) => text(s.id))),
  );
  const painting = useRef<boolean | null>(null);
  const paint = (slot: Data, available: boolean) => {
    const id = text(slot.id);
    set((previous) => {
      const next = new Set(previous);
      if (available) next.add(id);
      else next.delete(id);
      return next;
    });
    send("availability.paint", { day: slot.day, slot: id, available });
  };
  return (
    <Frame
      name="AvailabilityGrid"
      state={p.source === "calendar" ? "imported" : selected.size ? "painted" : "empty"}
    >
      <div
        className="f04-slot-grid"
        style={{ gridTemplateColumns: `44px repeat(${Math.max(1, days.length)}, minmax(0, 1fr))` }}
      >
        <span />
        {days.map((day) => (
          <span key={text(day.id)} className="f04-day">
            {label(day)}
          </span>
        ))}
        {times.map((time) => (
          <Fragment key={time}>
            <span className="f04-time">{time}</span>
            {days.map((day) => {
              const slot = slots.find((s) => s.day === day.id && label(s) === time);
              if (!slot) return <span key={text(day.id)} />;
              const available = selected.has(text(slot.id));
              return (
                <button
                  key={text(day.id)}
                  type="button"
                  className="f04-slot"
                  aria-label={`${label(day)} ${time}`}
                  aria-pressed={available}
                  onPointerDown={(event) => {
                    if (event.button !== 0) return;
                    painting.current = !available;
                    paint(slot, !available);
                  }}
                  onPointerEnter={(event) => {
                    if (
                      event.buttons === 1 &&
                      painting.current !== null &&
                      available !== painting.current
                    )
                      paint(slot, painting.current);
                  }}
                  onPointerUp={() => {
                    painting.current = null;
                  }}
                  onPointerCancel={() => {
                    painting.current = null;
                  }}
                  onClick={(event) => {
                    if (event.detail === 0) paint(slot, !available);
                  }}
                />
              );
            })}
          </Fragment>
        ))}
      </div>
      <div className="f04-availability-footer">
        <span className="f04-slot f04-free" aria-hidden="true" />
        <span>free</span>
        <span>
          drag to paint ·{" "}
          <button
            type="button"
            aria-label="Import calendar"
            onClick={() => send("availability.import")}
          >
            import from calendar
          </button>
        </span>
        <span className="f04-availability-privacy">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <rect x="5" y="11" width="14" height="10" rx="2" />
            <path d="M8 11V8a4 4 0 0 1 8 0v3" />
          </svg>
          only blinded slot tokens leave this device
        </span>
      </div>
    </Frame>
  );
}
