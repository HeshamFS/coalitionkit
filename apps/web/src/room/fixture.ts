// SPDX-License-Identifier: Apache-2.0
import type { ViewerState } from "../feed/delta";
export const roomFixture: ViewerState = {
  viewer: "p1",
  cost_meter: { spent: 0.04, currency: "EUR" },
  schedule: [{ task_id: "t1", title: "Review item", start: "10:00" }],
  privacy_notes: [
    { participant: "p2", knows: "Availability", notKnows: "Private notes", because: "Consent" },
  ],
  events: {
    c: {
      seq: 1,
      type: "coalition.charter",
      payload: {
        goal: "Coordinate the next step",
        participants: [{ id: "p1", display_name: "Member A" }],
      },
    },
    j: {
      seq: 2,
      type: "coalition.join",
      payload: { participant: "p1", card: { name: "Agent A", vendor: "Vendor A" } },
    },
    j2: { seq: 3, type: "coalition.join", payload: { card_url: "https://example.org/card" } },
    n: {
      seq: 4,
      type: "coalition.need",
      payload: { participant: "p1", description: "Review item", status: "owes" },
    },
    p: {
      seq: 5,
      type: "coalition.propose",
      payload: {
        plans: [{ plan_id: "plan-1", title: "Option A", objective_scores: { effort: 2 } }],
      },
    },
    d: {
      seq: 6,
      type: "coalition.decide",
      payload: { subject: { id: "plan-1", revision: 1 }, consent: true },
    },
  },
};
