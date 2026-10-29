// SPDX-License-Identifier: Apache-2.0
// The lens door shows one card and one step at a time. Three gestures drive it: tap, swipe next
// and swipe back; they only move between steps. Decisions stay on the phone (sheet 09b): a
// request is shown as a card that says so, and nothing is ever sent from the lens.

import type { OpenRequest } from "../feed/agent";
import type { ViewerState } from "../feed/delta";
import { deriveRoom, eventsOf } from "../feed/derive";

export type LensStep = {
  kind: "info" | "phone";
  id: string;
  eyebrow: string;
  title: string;
  body?: string;
};

export type Gesture = "tap" | "next" | "back";

export type LensState = { index: number };

export const START: LensState = { index: 0 };

const KIND_LABEL: Record<string, string> = {
  plan: "Plan",
  commitment: "Commitment",
  charter: "Charter",
  tension: "Choice",
  tension_option: "Choice",
};

export const PHONE_HINT = "Decide on your phone";

/** The steps for one viewer: where the coalition stands, then one step per open request. */
export function buildSteps(state: ViewerState | null, requests: OpenRequest[]): LensStep[] {
  const room = deriveRoom(state);
  const steps: LensStep[] = [
    {
      kind: "info",
      id: "now",
      eyebrow: room.stage,
      title: room.title,
      body: `${room.members} ${room.members === 1 ? "member" : "members"}`,
    },
    {
      kind: "info",
      id: "counts",
      eyebrow: "Your view",
      title: `${eventsOf(state).length} log entries`,
      body: `${room.counts.needs} needs · ${room.counts.offers} offers · ${room.counts.plans} plans`,
    },
  ];
  requests.forEach((r, n) => {
    steps.push({
      kind: "phone",
      id: r.id,
      eyebrow: `Asks you · ${n + 1} of ${requests.length} · ${KIND_LABEL[r.kind] ?? "Decision"}`,
      title: r.message,
      body: PHONE_HINT,
    });
  });
  return steps;
}

const clamp = (n: number, count: number) => Math.max(0, Math.min(n, Math.max(0, count - 1)));

/** One gesture: move between steps. It has no other effect. */
export function press(state: LensState, steps: LensStep[], gesture: Gesture): LensState {
  const index = clamp(state.index, steps.length);
  return { index: clamp(gesture === "back" ? index - 1 : index + 1, steps.length) };
}
