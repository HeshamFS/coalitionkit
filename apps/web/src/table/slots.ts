// SPDX-License-Identifier: Apache-2.0
// A time slot in the viewer's own time, from the `start` the host gives it. A slot without a
// readable start keeps the host's own label.
import type { Room } from "./room";

const STAMP = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/;

/** A surface's card fields hold host time stamps; each viewer reads them in their own time. */
export function localTimes(messages: unknown[]): unknown[] {
  return (messages as Record<string, { components?: Record<string, unknown>[] } | undefined>[]).map(
    (m) => {
      const parts = m?.updateComponents;
      if (!parts?.components) return m;
      const local = (v: unknown) =>
        typeof v === "string" && STAMP.test(v) ? slotLabel({ id: "", label: v, start: v }) : v;
      const components = parts.components.map((c) => {
        let out = c;
        if (Array.isArray(c.fields))
          out = {
            ...out,
            fields: (c.fields as Record<string, unknown>[]).map((f) => ({
              ...f,
              value: local(f.value),
            })),
          };
        // A timeline's items carry ISO times too: shown in the viewer's own time.
        if (c.component === "Timeline" && Array.isArray(c.items))
          out = {
            ...out,
            items: (c.items as Record<string, unknown>[]).map((i) => ({
              ...i,
              start: local(i.start),
              ...(i.end === undefined ? {} : { end: local(i.end) }),
            })),
          };
        return out;
      });
      return { ...m, updateComponents: { ...parts, components } };
    },
  );
}

export function slotLabel(slot: Room["slots"][number]): string {
  if (!slot.start || Number.isNaN(Date.parse(slot.start))) return slot.label;
  return new Date(slot.start).toLocaleString(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}
