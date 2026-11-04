// SPDX-License-Identifier: Apache-2.0
// Tool calls on the Table: the reader, the live strip, the cards and the sparks on the ring.
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { mockIo } from "../fixtureIo";
import { type Room, readRoom } from "../room";
import { SCENES } from "../scenes";
import { TableView } from "../TableView";
import { newestCalls } from "./ToolStrip";
import { readBusy, readTools, toolWords } from "./tools";

const call = (over: Record<string, unknown>) => ({
  id: "01J0000000000000000000000A",
  at: "2026-11-04T10:00:00+00:00",
  seq: 7,
  seat: "p1",
  agent: "hosted",
  tool: "model:offer",
  args: "choosing offers from its person's answers",
  result: "",
  status: "started",
  ms: 0,
  refs: [],
  ended: null,
  ...over,
});

function mount(room: Room, phone = false) {
  const scene = SCENES.find((s) => s.id === "work");
  if (!scene) throw new Error("work scene");
  render(
    <TableView
      room={room}
      state={scene.state}
      requests={[]}
      focus={null}
      setFocus={() => {}}
      answer={async () => undefined}
      outcome={async () => ({ ok: false, error: "no" }) as never}
      io={mockIo([])}
      phone={phone}
      owner={false}
      status="live"
    />,
  );
}

function roomWith(tools: unknown[], busySeat?: string): Room {
  const scene = SCENES.find((s) => s.id === "work");
  if (!scene) throw new Error("work scene");
  const base = scene.room;
  return {
    ...base,
    tools: readTools(tools),
    seats: base.seats.map((s) =>
      s.seat === busySeat
        ? { ...s, busy: { tool: "mcp:make_offer", args: "target need x", since: "now" } }
        : s,
    ),
  };
}

describe("tool calls", () => {
  it("reads room.tools and seats[].busy and never throws on junk", () => {
    expect(readTools("nope")).toEqual([]);
    expect(readTools([{ id: "x" }, 4, null])).toEqual([]);
    const [one] = readTools([call({ status: "weird", ms: -5, refs: ["a", 3] })]);
    expect(one?.status).toBe("started");
    expect(one?.ms).toBe(0);
    expect(one?.refs).toEqual(["a"]);
    expect(readBusy({ tool: "psi:compare", args: "a", since: "t" })?.tool).toBe("psi:compare");
    expect(readBusy({})).toBeNull();
    expect(toolWords("mcp:make_offer")).toEqual({ family: "MCP tool", name: "make offer" });
    const room = readRoom({ room: { seats: [], tools: [call({})] } } as never);
    expect(room?.tools).toHaveLength(1);
  });

  it("puts running calls first in the strip", () => {
    const tools = readTools([
      call({ id: "a", status: "done", ms: 812 }),
      call({ id: "b", status: "started" }),
      call({ id: "c", status: "failed", result: "refused: not_authorized" }),
    ]);
    expect(newestCalls(tools).map((t) => t.id)).toEqual(["b", "a", "c"]);
  });

  it("shows what the agents are doing, with real timings, and every call as a card", async () => {
    const room = roomWith([
      call({ id: "a", status: "done", ms: 1840, result: "muse, 900 tokens, $0.000500" }),
      call({
        id: "b",
        seat: "host",
        agent: "steward",
        tool: "steward:review",
        args: "offer from p2",
        status: "done",
        ms: 3,
        result: "allow",
      }),
      call({ id: "c", tool: "mcp:make_offer", args: "target need 01J", status: "started" }),
    ]);
    mount(room);
    const strip = screen.getByRole("region", { name: "What the agents are doing" });
    expect(strip).toHaveTextContent("1 running · 3 calls");
    expect(strip).toHaveTextContent("mcp:make_offer");
    expect(strip).toHaveTextContent("1.8 s · muse, 900 tokens");
    await userEvent.click(screen.getByRole("button", { name: "All calls" }));
    expect(document.querySelectorAll(".tk-cards [data-component='ToolCall']")).toHaveLength(3);
    expect(screen.getByText("Host · steward:review")).toBeInTheDocument();
  });

  it("sparks the seat whose agent has a call running, and hides the strip with no calls", () => {
    const scene = SCENES.find((s) => s.id === "work");
    const seat = scene?.room.seats.find((s) => s.kind !== "open")?.seat;
    mount(roomWith([], seat), true);
    expect(screen.queryByRole("region", { name: "What the agents are doing" })).toBeNull();
    const spark = document.querySelector(".tk-spark");
    expect(spark?.getAttribute("data-tool")).toBe("mcp:make_offer");
  });
});
