// SPDX-License-Identifier: Apache-2.0
// The measured strip. Only what the viewer's feed carries is shown; an unknown number is left out.
import type { ViewerState } from "../feed/delta";
import { deriveParticipants, eventsOf } from "../feed/derive";

export type Strip = {
  agents: string;
  vendors: string;
  seq: string;
  spent: string;
};

export function deriveStrip(state: ViewerState | null): Strip {
  const people = deriveParticipants(state);
  const vendors = new Set(people.map((p) => p.vendor).filter(Boolean));
  const events = eventsOf(state);
  const meter = (state?.cost_meter ?? {}) as { spent?: unknown; currency?: unknown };
  const spent =
    typeof meter.spent === "number" && Number.isFinite(meter.spent)
      ? `${meter.spent}${typeof meter.currency === "string" && meter.currency ? ` ${meter.currency}` : ""}`
      : "";
  return {
    // Every participant takes part through an agent (its own, or one the host runs for it).
    agents: people.length > 0 ? String(people.length) : "",
    vendors: vendors.size > 0 ? String(vendors.size) : "",
    seq: events.length ? String(events[events.length - 1]?.seq) : "",
    spent,
  };
}
