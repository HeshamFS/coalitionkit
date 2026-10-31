// SPDX-License-Identifier: Apache-2.0
// "View as": what another participant's public summary looks like to this viewer.
//
// Everything here is read from the viewer's own feed state, so nothing appears that the viewer
// does not already hold. The richer intersection view (the viewer's scope against the target's)
// is composed on the host later (slice S1b); `composeViewAs` is the seam where that response will
// replace this local summary.
import type { ViewerState } from "../feed/delta";
import { deriveParticipants, derivePrivateNotes } from "../feed/derive";
import { agentLine, type Pill, pillFor } from "./status";

export type ViewAsView = {
  targetId: string;
  label: string;
  seat: number;
  own: boolean;
  agent: string;
  pill: Pill | null;
  /** What the target shares with this viewer; null when nothing is shared. */
  shared: { item: string; detail: string } | null;
  /** Disclosure notes about the target that the viewer already holds. */
  notes: { knows: string; notKnows: string; because: string }[];
  caption: string;
};

export function composeViewAs(state: ViewerState | null, target: string): ViewAsView | null {
  const person = deriveParticipants(state).find((p) => p.id === target);
  if (!person) return null;
  const own = person.id === state?.viewer;
  return {
    targetId: person.id,
    label: person.label,
    seat: person.seat,
    own,
    agent: agentLine(person.agent, person.vendor),
    pill: pillFor(person.status, { own, hasItem: Boolean(person.item) }),
    shared: person.item ? { item: person.item, detail: person.detail } : null,
    notes: derivePrivateNotes(state)
      .filter((n) => n.participant === person.id)
      .map(({ knows, notKnows, because }) => ({ knows, notKnows, because })),
    caption: `as ${person.label} would see it, limited to what you may see`,
  };
}
