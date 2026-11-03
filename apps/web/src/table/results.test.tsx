// SPDX-License-Identifier: Apache-2.0
// Results as the engine builds them (`fixed_tree` in `room/results.py`): every kind renders in
// full, no card is empty, and provenance shows once, on the card.
import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SurfaceBook } from "../feed/surfaces";
import { ENGINE_RESULTS, emptyPlace } from "./engineResults";
import { ComposedSurface } from "./useSurface";

const cardsIn = (tree: unknown[]) =>
  (tree as { component?: string }[]).filter((n) => n.component === "Card").length;

describe("results by kind", () => {
  it("covers the five kinds of the contract", () => {
    expect(ENGINE_RESULTS.map((r) => r.kind)).toEqual([
      "place",
      "schedule",
      "budget",
      "list",
      "draft",
    ]);
  });

  for (const r of [...ENGINE_RESULTS, emptyPlace]) {
    it(`${r.kind} (${r.id}) draws through the catalog, in full`, () => {
      const book = new SurfaceBook(() => {});
      book.apply("x", r.messages);
      expect(book.list()[0]?.fallback).toBe(false);

      const { container } = render(<ComposedSurface messages={r.messages} />);
      const cards = [...container.querySelectorAll(".f01-root-Card")];
      // Every card the tree names is on screen, and each has something in it.
      expect(cards).toHaveLength(cardsIn(r.tree));
      expect(cards.length).toBeGreaterThan(0);
      for (const c of cards) {
        const filled = c.querySelectorAll("dd, a2ui-react-text").length;
        expect(filled, c.getAttribute("id") ?? "").toBeGreaterThan(0);
        // Provenance once, at card level, and not again on each line.
        expect(c.querySelectorAll(".badge")).toHaveLength(1);
      }
      expect(container.querySelectorAll(".badge")).toHaveLength(cards.length);
    });
  }

  it("shows every option, item and step the data holds", () => {
    const text = (id: string) => {
      const r = ENGINE_RESULTS.find((x) => x.id === id);
      return render(<ComposedSurface messages={r?.messages ?? []} />).container.textContent ?? "";
    };
    expect(text("r1")).toContain("Venue 2");
    expect(text("r2")).toContain("Open");
    expect(text("r2")).toContain("Send the invitation");
    expect(text("r3")).toContain("Time people offered, in minutes");
    expect(text("r4")).toContain("A van");
    expect(text("r5")).toContain("Bring a friend.");
  });

  it("says plainly when no place has been named", () => {
    const { container } = render(<ComposedSurface messages={emptyPlace.messages} />);
    expect(container.textContent).toContain("No place has been named yet");
  });
});
