// SPDX-License-Identifier: Apache-2.0
import { describe, expect, it } from "vitest";
import { roomFixture } from "../room/fixture";
import {
  deriveDecisions,
  deriveMetrics,
  deriveParticipants,
  derivePlans,
  derivePrivateNotes,
} from "./derive";

describe("room projection derivations", () => {
  it("uses explicit identity and names, with neutral fallback", () => {
    const people = deriveParticipants(roomFixture);
    expect(people[0]).toMatchObject({
      id: "p1",
      label: "Member A",
      agent: "Agent A",
      vendor: "Vendor A",
      item: "Review item",
    });
    expect(people[1]).toMatchObject({ label: "Member 2", item: "", agent: "" });
  });
  it("reads nested proposed plans with sourced scores and no decision capability", () => {
    expect(derivePlans(roomFixture)[0]).toMatchObject({
      id: "plan-1",
      label: "A · Option A",
      canDecide: false,
      objectives: [{ name: "effort", value: { value: 2, event_ref: "p" } }],
    });
  });
  it("counts only visible data and omits unsourced metrics", () => {
    expect(deriveMetrics(roomFixture)).toEqual([
      { label: "Agents", value: 1 },
      { label: "Vendors", value: 1 },
      { label: "Spent (EUR)", value: 0.04 },
    ]);
    expect(deriveMetrics(null)).toEqual([]);
    expect(derivePrivateNotes(null)).toEqual([]);
  });
  it("derives consent without inventing signer or verification", () => {
    expect(deriveDecisions(roomFixture)).toEqual([
      { seq: 6, subject: "plan-1", revision: 1, answer: "yes", time: "", participant: "" },
    ]);
  });
  it("does not attribute anonymous needs to an arbitrary participant", () => {
    const state = {
      events: {
        j: { seq: 1, type: "coalition.join", payload: { card_url: "card" } },
        n: { seq: 2, type: "coalition.need", payload: { description: "Anonymous item" } },
      },
    };
    expect(deriveParticipants(state)[0]?.item).toBe("");
  });
  it("deduplicates rejoined members and revised plans", () => {
    const events = roomFixture.events as Record<string, unknown>;
    const state = {
      events: {
        ...events,
        j3: {
          seq: 7,
          type: "coalition.join",
          payload: { participant: "p1", display_name: "Updated member" },
        },
        p2: {
          seq: 8,
          type: "coalition.propose",
          payload: { plans: [{ plan_id: "plan-1", title: "Updated option" }] },
        },
      },
    };
    expect(deriveParticipants(state)).toHaveLength(2);
    expect(deriveParticipants(state)[0]?.label).toBe("Updated member");
    expect(derivePlans(state)).toHaveLength(1);
    expect(derivePlans(state)[0]?.label).toBe("A · Updated option");
  });
});

it("links delivered authors and proposal assignments without inventing agents", () => {
  const state = {
    viewer: "p1",
    events: {
      j: { seq: 1, type: "coalition.join", on_behalf_of: "p1", payload: {} },
      n: {
        seq: 2,
        type: "coalition.need",
        on_behalf_of: "host",
        payload: { need_id: "t1", description: "Review item" },
      },
      p: {
        seq: 3,
        type: "coalition.propose",
        payload: {
          plans: [{ plan_id: "plan1", assignments: [{ assignee: "p1", task_id: "t1" }] }],
        },
      },
    },
  };
  expect(deriveParticipants(state)[0]).toMatchObject({
    id: "p1",
    item: "Review item",
    status: "Needs their yes",
    agent: "",
  });
  const committed = {
    ...state,
    events: {
      ...state.events,
      c: {
        seq: 4,
        type: "coalition.commit",
        on_behalf_of: "p1",
        payload: { task_id: "t1", commitment_id: "c1", status: "pending" },
      },
      d: {
        seq: 5,
        type: "coalition.decide",
        on_behalf_of: "p1",
        payload: { subject: { id: "c1" }, consent: true },
      },
    },
  };
  expect(deriveParticipants(committed)[0]?.status).toBe("Agreed");
  expect(
    deriveParticipants({
      ...committed,
      events: {
        ...committed.events,
        changed: {
          seq: 6,
          type: "coalition.ripple",
          on_behalf_of: "p1",
          payload: { invalidates: ["t1"], change: "Requirements changed" },
        },
      },
    })[0]?.status,
  ).toBe("Changed · ripple");
});

it("uses newer assignments instead of a previous commitment's task", () => {
  const state = {
    events: {
      j: { seq: 1, type: "coalition.join", on_behalf_of: "p1", payload: {} },
      n1: {
        seq: 2,
        type: "coalition.need",
        payload: { need_id: "t1", description: "Previous item" },
      },
      c: {
        seq: 3,
        type: "coalition.commit",
        on_behalf_of: "p1",
        payload: { task_id: "t1", commitment_id: "c1", status: "pending" },
      },
      n2: {
        seq: 4,
        type: "coalition.need",
        payload: { need_id: "t2", description: "Current item" },
      },
      p: {
        seq: 5,
        type: "coalition.propose",
        payload: {
          plans: [{ plan_id: "option", assignments: [{ assignee: "p1", task_id: "t2" }] }],
        },
      },
    },
  };
  expect(deriveParticipants(state)[0]?.item).toBe("Current item");
});
