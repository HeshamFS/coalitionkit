// SPDX-License-Identifier: Apache-2.0
// The measured strip. Only what the viewer's feed carries is shown; the rest stays a placeholder.
import type { ViewerState } from "../feed/delta";
import { deriveParticipants, eventsOf } from "../feed/derive";

export const MEASURED = "[MEASURED]";

export type Strip = {
  agents: string;
  vendors: string;
  calendars: string;
  elapsed: string;
  seq: string;
  spent: string;
};

const count = (n: number) => (n > 0 ? String(n) : MEASURED);

export function deriveStrip(state: ViewerState | null): Strip {
  const people = deriveParticipants(state);
  const vendors = new Set(people.map((p) => p.vendor).filter(Boolean));
  const events = eventsOf(state);
  const meter = (state?.cost_meter ?? {}) as { spent?: unknown; currency?: unknown };
  const spent =
    typeof meter.spent === "number" && Number.isFinite(meter.spent)
      ? `${meter.spent}${typeof meter.currency === "string" && meter.currency ? ` ${meter.currency}` : ""}`
      : MEASURED;
  return {
    // Every participant takes part through an agent (its own, or one the host runs for it).
    agents: count(people.length),
    vendors: vendors.size > 0 ? String(vendors.size) : "",
    calendars: MEASURED,
    elapsed: MEASURED,
    seq: events.length ? String(events[events.length - 1]?.seq) : MEASURED,
    spent,
  };
}
