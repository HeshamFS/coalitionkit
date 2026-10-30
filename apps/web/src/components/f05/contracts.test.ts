// SPDX-License-Identifier: Apache-2.0
import { describe, expect, it } from "vitest";
import { apis as f05 } from "../../catalog/families/f05";
import { apis as f06 } from "../../catalog/families/f06";
import { apis as f07 } from "../../catalog/families/f07";

const bound = { value: 3, event_ref: "event:1" };
describe("catalog provenance and required props", () => {
  it("rejects unbound numbers at any depth", () => {
    expect(f05.ParticipantCard.schema.safeParse({ seat: 3 }).success).toBe(false);
    expect(f06.FairnessMeter.schema.safeParse({ rows: [{ share: 30 }] }).success).toBe(false);
    expect(f07.MapView.schema.safeParse({ points: [{ lat: { value: 3 } }] }).success).toBe(false);
    expect(f07.MapView.schema.safeParse({ points: [{ lat: bound }] }).success).toBe(true);
  });
  it("requires the tension's full revision-bound subject and deadline", () => {
    const props = {
      options: [],
      deciders: [],
      decision_deadline: "2030-01-01T00:00:00Z",
      subject: { kind: "tension_option", id: "t1", revision: bound },
    };
    expect(f06.TensionCard.schema.safeParse(props).success).toBe(true);
    expect(
      f06.TensionCard.schema.safeParse({ ...props, subject: { kind: "tension_option", id: "t1" } })
        .success,
    ).toBe(false);
    expect(
      f06.TensionCard.schema.safeParse({ ...props, decision_deadline: undefined }).success,
    ).toBe(false);
  });
  it("retains the plan list bound", () => {
    expect(
      f06.PlanCompare.schema.safeParse({ plans: Array.from({ length: 9 }, () => ({ id: "p1" })) })
        .success,
    ).toBe(false);
  });
  it("accepts bindings and enforces required titles", () => {
    expect(f05.CoalitionHeader.schema.safeParse({ title: { path: "/title" } }).success).toBe(true);
    expect(f05.CoalitionHeader.schema.safeParse({}).success).toBe(false);
    expect(f06.PlanCompare.schema.safeParse({}).success).toBe(false);
  });
});
