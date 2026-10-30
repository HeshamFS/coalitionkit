// SPDX-License-Identifier: Apache-2.0
import type { ComponentContext } from "@a2ui/web_core/v0_9";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Sheet11 } from "../../gallery/sheets/Sheet11";
import { examples } from "./examples";
import { render as draw } from "./render";

afterEach(cleanup);
const bound = (value: number) => ({ value, event_ref: "test:1" });
function component(name: string, props: Record<string, unknown>) {
  const dispatchAction = vi.fn();
  render(draw(name, props, { dispatchAction } as unknown as ComponentContext));
  return dispatchAction;
}
describe("family 11 panel fidelity", () => {
  it("renders all panels with headings first and no fallback", () => {
    const { container } = render(<Sheet11 />);
    expect(container.querySelector("[data-fallback]")).toBeNull();
    const panels = container.querySelectorAll("[data-panel]");
    expect(panels).toHaveLength(13);
    for (const panel of panels) expect(panel.firstElementChild?.className).toBe("head");
    for (const example of examples)
      expect(container.querySelector(`section[data-component="${example.name}"]`)).not.toBeNull();
  });
  it("formats metered costs and handles both budget thresholds", () => {
    const props = {
      budget: bound(3),
      total: bound(0.71),
      rows: [{ role: "member", model: "model", cost: bound(0.19) }],
    };
    component("CostMeter", props);
    expect(screen.getByText("€0.71")).toBeVisible();
    expect(screen.getByText("of €3 budget")).toBeVisible();
    expect(screen.getByText("€0.19")).toBeVisible();
    cleanup();
    component("CostMeter", { ...props, total: bound(2.4) });
    expect(screen.getByText("Warning · 80% of budget")).toBeVisible();
    cleanup();
    component("CostMeter", { ...props, total: bound(3) });
    expect(screen.getByText("Stopped · budget reached")).toBeVisible();
  });
  it("saves only selected non-judgement lessons", () => {
    const lessons = [
      { text: "Confirm availability", scope: "private", kind: "coordination", from: ["e1"] },
      { text: "Reserve time", scope: "shareable", kind: "timing", from: ["e2"] },
      { text: "Unreliable member", scope: "private", kind: "judgement", from: ["e3"] },
    ];
    const dispatch = component("LessonReview", { lessons });
    expect(screen.getByLabelText(/Unreliable member/)).toBeDisabled();
    fireEvent.click(screen.getByLabelText(/Reserve time/));
    expect(screen.getByText("1 of 3 selected")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Save selected lessons" }));
    expect(dispatch).toHaveBeenCalledWith({
      event: { name: "lessons.save", context: { lessons: [lessons[0]] } },
    });
  });
  it("opens the selected archive record and retains its raw date", () => {
    const dispatch = component("CoalitionArchive", {
      items: [
        {
          coalition: "c1",
          ended: "2026-11-09T12:40:00Z",
          outcome: "reached",
          yourCost: "€0.24",
          pack: "none",
        },
      ],
    });
    expect(screen.getByText("Mon 9 Nov")).toHaveAttribute("dateTime", "2026-11-09T12:40:00Z");
    fireEvent.click(screen.getByRole("button", { name: "Open c1" }));
    expect(dispatch).toHaveBeenCalledWith({
      event: { name: "archive.open", context: { id: "c1" } },
    });
  });
});
