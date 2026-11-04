// SPDX-License-Identifier: Apache-2.0
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { base } from "../fixtures";
import { readRoom, type SharedSet } from "../room";
import { SharedSets, setFinding, setNote } from "./SharedSets";

const overlap: SharedSet = {
  id: "colours",
  label: "Colours we all like",
  mode: "overlap",
  state: "done",
  values: ["blue", "green"],
  count: 2,
  compared: 3,
  event: "e1",
};
const count: SharedSet = {
  ...overlap,
  id: "words",
  label: "Words",
  mode: "count",
  values: null,
  count: 1,
};

describe("compared sets", () => {
  it("reads the host's sets and the viewer's own counts, dropping what is off", () => {
    const room = readRoom({
      room: {
        sets: [overlap, { id: "" }, { id: "x", mode: "all", state: 4, values: "no", count: "2" }],
        mine: { sets: { colours: 1, words: -2, x: "3" } },
      },
    });
    expect(room?.sets?.[0]).toEqual({ ...overlap, values: ["blue", "green"] });
    expect(room?.sets?.[1]).toMatchObject({ id: "x", mode: "overlap", state: "asking" });
    expect(room?.sets?.[1]?.values).toBeNull();
    expect(room?.mine.sets).toEqual({ colours: 1 });
  });

  it("says only what the host published, and what stayed private for this viewer", () => {
    expect(setFinding({ ...overlap })).toBe("Fits all 3");
    expect(setFinding({ ...count })).toBe("1 in common, which ones stays private");
    expect(setFinding({ ...overlap, values: [], compared: 2 })).toBe("Nothing fits you both");
    expect(setNote({ ...overlap }, 1)).toBe("Compared by 3. Your other 1 stayed private.");
    expect(setNote({ ...overlap }, undefined)).toBe("Compared by 3. You sat this one out.");
    expect(setNote({ ...overlap, state: "crossing" }, 1)).toBe("Comparing privately…");
    expect(setNote({ ...overlap, values: null, count: null }, undefined)).toBe(
      "Too few gave theirs; nothing was shared.",
    );
  });

  it("shows each set on the Table, with the shared values as chips", () => {
    const room = base({ sets: [{ ...overlap }, { ...count }] });
    room.mine.sets = { colours: 1, words: 2 };
    render(<SharedSets room={room} />);
    const panel = screen.getByRole("region", { name: "Found in common, privately" });
    const chips = within(panel)
      .getAllByRole("listitem")
      .map((li) => li.textContent);
    expect(chips).toEqual(["blue", "green"]);
    expect(panel.textContent).toContain("Your other 2 stayed private.");
    expect(panel.textContent).not.toContain("undefined");
  });

  it("is absent when no pack declared a set", () => {
    const { container } = render(<SharedSets room={base({})} />);
    expect(container.textContent).toBe("");
  });
});
