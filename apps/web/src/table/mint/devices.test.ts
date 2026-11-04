// SPDX-License-Identifier: Apache-2.0
import { describe, expect, it } from "vitest";
import { readRoom } from "../room";
import { readDevices } from "./deviceData";

const device = {
  id: "device-1",
  label: "Shared unit",
  template: "resource",
  state: "seated",
  health: "live",
  mine: true,
  can_approve: false,
  stages: [{ name: "capture", state: "done", took: 0.4 }],
  tools: ["list_free_slots", "hold_slot"],
  needs: [{ id: "n1", title: "Book the shared unit" }],
  attacks: { passed: 9, total: 9 },
  cost_micro_usd: 1200,
  elapsed: 14.2,
  fields: [],
  reading: [{ field: "field_1", value: 61, unit: "count", threshold: 50, over: true }],
  readings: [{ field: "field_1", value: 61, t: 1_700_000_000 }],
  hold: { need: "n1", start: "09:00", end: "09:30", state: "confirmed" },
};

describe("room.devices", () => {
  it("reads what the host sent and nothing it did not", () => {
    const [d] = readDevices({ room: { devices: [device, { label: "no id" }] } });
    expect(d?.hold).toEqual({ need: "n1", start: "09:00", end: "09:30", state: "confirmed" });
    expect(d?.reading[0]?.over).toBe(true);
    expect(d?.attacks).toEqual({ passed: 9, total: 9 });
    expect(readDevices({ room: { devices: [device, { label: "no id" }] } })).toHaveLength(1);
  });

  it("drops anything off and defaults the rest", () => {
    const [d] = readDevices({ room: { devices: [{ id: "x", state: "odd", hold: "no" }] } });
    expect(d?.state).toBe("failed");
    expect(d?.hold).toBeNull();
    expect(d?.health).toBe("offline");
    expect(readDevices(null)).toEqual([]);
  });

  it("keeps a device seat a device on the ring", () => {
    const seat = { seat: "device-1", role: "member", label: "Shared unit", kind: "device" };
    const room = readRoom({ room: { phase: "work", seats: [seat] } });
    expect(room?.seats[0]?.kind).toBe("device");
  });
});
