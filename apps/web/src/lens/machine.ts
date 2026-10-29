// SPDX-License-Identifier: Apache-2.0
// The lens door shows one card and one step at a time. Three gestures drive it: tap (confirm),
// swipe next and swipe back. Nothing is sent on a first tap: every action goes through a confirm
// step, and a swipe there cancels it.

import type { OpenRequest } from "../feed/agent";
import type { ViewerState } from "../feed/delta";
import { deriveRoom, eventsOf } from "../feed/derive";

export type LensStep =
  | { kind: "info"; id: string; eyebrow: string; title: string; body?: string }
  | { kind: "ask"; id: string; eyebrow: string; title: string; body?: string; request: OpenRequest }
  /** A request the lens cannot answer on its own (an option has to be chosen): the phone does. */
  | { kind: "phone"; id: string; eyebrow: string; title: string; body?: string };

export type Gesture = "tap" | "next" | "back";

export type LensState = {
  index: number;
  /** Set while the confirm step is showing: the answer that a second tap would send. */
  confirming: { consent: boolean } | null;
  /** A one-line result shown once after an answer was sent. */
  ack: string | null;
};

export const START: LensState = { index: 0, confirming: null, ack: null };

const KIND_LABEL: Record<string, string> = {
  plan: "Plan",
  commitment: "Commitment",
  charter: "Charter",
  tension: "Choice",
  tension_option: "Choice",
};

/** The steps for one viewer: where the coalition stands, then one step per open request. */
export function buildSteps(
  state: ViewerState | null,
  requests: OpenRequest[],
  sent: ReadonlySet<string> = new Set(),
): LensStep[] {
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
  const open = requests.filter((r) => !sent.has(r.id));
  open.forEach((r, n) => {
    const label = KIND_LABEL[r.kind] ?? "Decision";
    const eyebrow = `Asks you · ${n + 1} of ${open.length}`;
    if (r.kind === "tension_option") {
      steps.push({
        kind: "phone",
        id: r.id,
        eyebrow,
        title: r.message,
        body: `${label}: choose on your phone`,
      });
    } else {
      steps.push({ kind: "ask", id: r.id, eyebrow, title: r.message, body: label, request: r });
    }
  });
  return steps;
}

export type Press = { state: LensState; send?: { request: OpenRequest; consent: boolean } };

const clamp = (n: number, count: number) => Math.max(0, Math.min(n, Math.max(0, count - 1)));

/** One gesture. Pure: the caller sends `send` to the host and records the request as sent. */
export function press(state: LensState, steps: LensStep[], gesture: Gesture): Press {
  if (state.ack !== null) return { state: { ...state, ack: null } };
  const index = clamp(state.index, steps.length);
  const step = steps[index];
  if (state.confirming && step?.kind === "ask") {
    if (gesture === "tap") {
      return {
        state: { index, confirming: null, ack: "Answer sent" },
        send: { request: step.request, consent: state.confirming.consent },
      };
    }
    return { state: { index, confirming: null, ack: null } };
  }
  if (step?.kind === "ask") {
    if (gesture === "tap") return { state: { index, confirming: { consent: true }, ack: null } };
    if (gesture === "next") return { state: { index, confirming: { consent: false }, ack: null } };
    return { state: { index: clamp(index - 1, steps.length), confirming: null, ack: null } };
  }
  const to = gesture === "back" ? index - 1 : index + 1;
  return { state: { index: clamp(to, steps.length), confirming: null, ack: null } };
}
