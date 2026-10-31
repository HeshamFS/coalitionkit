// SPDX-License-Identifier: Apache-2.0
import type { ViewerState } from "../feed/delta";

/** Neutral feed state for review pages and tests. Viewer is p1; no scenario data. */
export const momentsFixture: ViewerState = {
  viewer: "p1",
  // The host's sender-only refusals: what the Steward blocked for this viewer's own agent.
  refusals: [
    {
      type: "coalition.offer",
      code: "steward_blocked",
      policy: "no-contact-before-consent",
      at: "2026-10-31T12:00:00Z",
    },
  ],
  events: {
    j1: {
      seq: 1,
      type: "coalition.join",
      on_behalf_of: "p1",
      payload: { participant: "p1", card: { name: "Agent 1", vendor: "ChatGPT" } },
    },
    j2: {
      seq: 2,
      type: "coalition.join",
      on_behalf_of: "p2",
      payload: { participant: "p2", card: { name: "Agent 2", vendor: "Claude" } },
    },
    j3: {
      seq: 3,
      type: "coalition.join",
      on_behalf_of: "p3",
      payload: { participant: "p3", card: { name: "Agent 3", vendor: "Muse" } },
    },
    t1: { seq: 4, type: "coalition.need", payload: { need_id: "t1", description: "task t1" } },
    t2: {
      seq: 5,
      type: "coalition.task",
      payload: { task_id: "t2", title: "task t2", depends_on: ["t1"], status: "open" },
    },
    t3: {
      seq: 6,
      type: "coalition.task",
      payload: { task_id: "t3", title: "task t3", depends_on: ["t1"] },
    },
    t4: {
      seq: 7,
      type: "coalition.task",
      payload: { task_id: "t4", title: "task t4", depends_on: ["t2", "t3"] },
    },
    t5: { seq: 8, type: "coalition.task", payload: { task_id: "t5", title: "task t5" } },
    t6: {
      seq: 9,
      type: "coalition.task",
      payload: { task_id: "t6", title: "task t6", depends_on: ["t5"] },
    },
    o1: {
      seq: 10,
      type: "coalition.offer",
      on_behalf_of: "p1",
      payload: { offer_id: "o1", target: { id: "t1" }, cost: { effort: 2 } },
    },
    a1: {
      seq: 11,
      type: "coalition.answer",
      on_behalf_of: "p2",
      payload: { query_id: "q1", result: "yes" },
    },
    m1: {
      seq: 12,
      type: "coalition.match",
      on_behalf_of: "p1",
      payload: {
        match_id: "m1",
        task_id: "t2",
        peer: "p2",
        round: "request",
        blob: "Zm9vYmFy-AAA1",
      },
    },
    m2: {
      seq: 13,
      type: "coalition.match",
      on_behalf_of: "p2",
      payload: {
        match_id: "m1",
        task_id: "t2",
        peer: "p1",
        round: "response",
        blob: "YmF6cXV4-BBB2",
      },
    },
    p1: {
      seq: 15,
      type: "coalition.propose",
      payload: {
        plans: [{ plan_id: "plan-1", assignments: [{ assignee: "p2", task_id: "t3" }] }],
      },
    },
    c1: {
      seq: 16,
      type: "coalition.commit",
      on_behalf_of: "p2",
      payload: { commitment_id: "c1", task_id: "t3", status: "pending" },
    },
    r1: {
      seq: 17,
      type: "coalition.ripple",
      on_behalf_of: "p3",
      payload: { change: "a dependency moved", task_id: "t1", invalidates: ["t3", "t4"] },
    },
  },
};
