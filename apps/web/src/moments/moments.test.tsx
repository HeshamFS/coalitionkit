// SPDX-License-Identifier: Apache-2.0
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { overlapFrom, rippleFrom, theatreFrom } from "./adapters";
import { momentsFixture } from "./fixture";
import { layout, rippleCounts } from "./graph";
import { MomentsDemo } from "./MomentsDemo";
import { Overlap } from "./Overlap";
import { Ripple } from "./Ripple";
import { slot, Theatre } from "./Theatre";

describe("theatreFrom", () => {
  const t = theatreFrom(momentsFixture);
  it("builds one cursor per joined agent with vendor and join-order seat", () => {
    expect(t.agents.map((a) => [a.label, a.vendor, a.seat])).toEqual([
      ["Member 1", "ChatGPT", 1],
      ["Member 2", "Claude", 2],
      ["Member 3", "Muse", 3],
    ]);
    expect(t.counts).toEqual({ agents: 3, vendors: 3, decisions: 1 });
  });
  it("takes bubbles from real events authored by that agent", () => {
    expect(t.agents[0]?.bubbles.map((b) => b.summary)).toEqual([
      "offer · cost 2 · no reasons",
      "match · blinded points sent",
    ]);
    expect(t.agents[1]?.bubbles.map((b) => b.summary)).toEqual([
      "vault answer · yes",
      "match · blinded points returned",
      "commit · pending",
    ]);
    expect(t.agents[0]?.bubbles[0]?.message.seq).toBe(10);
  });
  it("shows the latest host action and steward interventions with the policy", () => {
    expect(t.gardener.doing).toBe("drafting a plan");
    expect(t.steward[0]?.policy).toBe("no-contact-before-consent");
  });
  it("shows a pack policy the host enforced, with its name", () => {
    const refusals = [
      { type: "coalition.offer", code: "pack_violation", policy: "daily-no-contact", at: "t" },
      { type: "coalition.offer", code: "schema_invalid", at: "t" },
    ];
    const p = theatreFrom({ ...momentsFixture, refusals });
    expect(p.steward.map((s) => [s.policy, s.summary])).toEqual([
      ["daily-no-contact", "blocked your agent's offer"],
    ]);
  });
  it("invents nothing from an empty state", () => {
    const e = theatreFrom(null);
    expect(e.agents).toEqual([]);
    expect(e.steward).toEqual([]);
    expect(e.gardener.doing).toBe("waiting");
  });
  it("places cursors at the same spot every time", () => {
    expect(slot(1, 3)).toEqual(slot(1, 3));
  });
  it("opens the real message from a bubble", async () => {
    render(<Theatre {...t} />);
    await userEvent.click(screen.getByRole("button", { name: "offer · cost 2 · no reasons" }));
    expect(screen.getByText(/seq 10 · coalition.offer/)).toBeTruthy();
    expect(screen.getByText(/"offer_id": "o1"/)).toBeTruthy();
  });
});

describe("overlapFrom and Overlap", () => {
  it("takes crossings from match rounds with direction by author, as fingerprints", () => {
    const o = overlapFrom(momentsFixture);
    expect(o.crossings.map((c) => [c.seq, c.dir])).toEqual([
      [12, "out"],
      [13, "in"],
    ]);
    expect(o.crossings[0]?.fingerprint).toMatch(/^[0-9a-f]{4}…[0-9a-f]{2}$/);
    expect(o.result).toBeUndefined();
  });
  it("never shows a result unless the prop is given", () => {
    render(<Overlap {...overlapFrom(momentsFixture)} />);
    expect(screen.queryByText(/Shared:/)).toBeNull();
    expect(screen.getByText(/appears only on each member's own screen/)).toBeTruthy();
    expect(screen.getByText("Your vault is held by your agent")).toBeTruthy();
  });
  it("shows the result and own vault when given, and no entries for the other side", () => {
    render(
      <Overlap
        {...overlapFrom(momentsFixture, {
          vault: ["slot 1", "slot 2"],
          theirCount: 3,
          result: { shared: "slot 2", keptPrivate: 1 },
        })}
      />,
    );
    expect(screen.getByText("Shared: slot 2")).toBeTruthy();
    expect(screen.getByText("your other 1 stayed private")).toBeTruthy();
    expect(screen.getByText("3 entries")).toBeTruthy();
    expect(screen.getByText("never leaves their circle")).toBeTruthy();
  });
  it("does not put the raw blob on screen", () => {
    const { container } = render(<Overlap {...overlapFrom(momentsFixture)} />);
    expect(container.textContent).not.toContain("Zm9vYmFy");
  });
});

describe("rippleFrom and Ripple", () => {
  const r = rippleFrom(momentsFixture);
  it("reads tasks, dependencies and the ripple from the events", () => {
    expect(r.nodes.map((n) => n.id)).toEqual(["t1", "t2", "t3", "t4", "t5", "t6"]);
    expect(r.edges).toContainEqual({ from: "t3", to: "t4" });
    expect(r.ripple?.invalidated).toEqual(["t3", "t4"]);
    expect(r.peopleAsked).toBe(1);
    expect(r.measuredMs).toBeUndefined();
  });
  it("counts touched against untouched", () => {
    expect(rippleCounts(r.nodes, r.ripple)).toMatchObject({ k: 2, n: 6, rest: 4 });
  });
  it("lays out by dependency depth, deterministically", () => {
    const a = layout(r.nodes, r.edges).placed.map((p) => [p.id, p.depth]);
    expect(a).toEqual([
      ["t1", 0],
      ["t2", 1],
      ["t3", 1],
      ["t4", 2],
      ["t5", 0],
      ["t6", 1],
    ]);
    expect(layout(r.nodes, r.edges)).toEqual(layout(r.nodes, r.edges));
  });
  it("survives a cycle", () => {
    const l = layout(
      [
        { id: "a", label: "a" },
        { id: "b", label: "b" },
      ],
      [
        { from: "a", to: "b" },
        { from: "b", to: "a" },
      ],
    );
    expect(l.placed).toHaveLength(2);
  });
  it("pulses only touched nodes and states the counter", () => {
    const { container } = render(<Ripple {...r} />);
    const pulsing = [...container.querySelectorAll('[data-pulse="true"]')].map((n) =>
      n.getAttribute("data-task"),
    );
    expect(pulsing).toEqual(["t3", "t4"]);
    expect(container.querySelectorAll('.mo-node[data-pulse="false"]')).toHaveLength(4);
    expect(screen.getByText(/tasks re-planned/).textContent).toBe("2 of 6 tasks re-planned");
    expect(screen.getByText(/untouched/).textContent).toContain("1 person asked again");
    expect(screen.queryByText(/change to every affected screen/)).toBeNull();
    expect(screen.getByText("coalition.ripple · invalidates 2 tasks")).toBeTruthy();
  });
  it("shows a measured value only when provided and does nothing without a ripple", () => {
    const { container } = render(<Ripple nodes={r.nodes} edges={r.edges} measuredMs={120} />);
    expect(container.querySelectorAll('[data-pulse="true"]')).toHaveLength(0);
    expect(screen.getByText("120 ms")).toBeTruthy();
  });
});

describe("MomentsDemo", () => {
  it("renders the three views", () => {
    render(<MomentsDemo />);
    expect(screen.getByLabelText("Theatre")).toBeTruthy();
    expect(screen.getByLabelText("Overlap")).toBeTruthy();
    expect(screen.getByLabelText("Ripple")).toBeTruthy();
  });
});
