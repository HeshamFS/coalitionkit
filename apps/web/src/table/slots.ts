// SPDX-License-Identifier: Apache-2.0
// A time slot in the viewer's own time, from the `start` the host gives it. A slot without a
// readable start keeps the host's own label.
import type { Room } from "./room";

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
