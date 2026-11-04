// SPDX-License-Identifier: Apache-2.0
// "View as": what another participant's public summary looks like to this viewer.
//
// The browser cannot see another participant's scope, so it cannot compute the intersection of
// the viewer's scope and the target's. Locally it shows only public membership facts (seat, agent,
// status). Anything richer comes from the host's intersection view, and
// `composeViewAs` is the seam where that response replaces this summary.
import type { ViewerState } from "../feed/delta";
import { deriveParticipants } from "../feed/derive";
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
    shared: null,
    notes: [],
    caption: `as ${person.label} appears to everyone: seat, agent and status`,
  };
}
