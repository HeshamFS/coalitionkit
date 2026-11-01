// SPDX-License-Identifier: Apache-2.0
import { A2uiSurface } from "@a2ui/react/v0_9";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { SurfaceBook } from "../../feed/surfaces";
import { Sheet06 } from "../../gallery/sheets/Sheet06";
import { examples } from "./examples";

afterEach(cleanup);
function surface(name: string, props: Record<string, unknown>) {
  const dispatch = vi.fn();
  const book = new SurfaceBook(dispatch);
  book.apply("f06", [
    { version: "v0.9", createSurface: { surfaceId: "f06", catalogId: "coalitionkit/v0_9" } },
    {
      version: "v0.9",
      updateComponents: {
        surfaceId: "f06",
        components: [{ id: "root", component: name, ...props }],
      },
    },
    { version: "v0.9", updateDataModel: { surfaceId: "f06", path: "/", value: {} } },
  ]);
  const entry = book.list()[0];
  if (!entry || entry.fallback) throw new Error("Catalog fallback");
  const view = render(<A2uiSurface surface={entry.model} />);
  return { ...view, dispatch };
}
it("renders every family component through the catalog without fallback", () => {
  const { container } = render(<Sheet06 />);
  expect(container.querySelector("[data-fallback]")).toBeNull();
  for (const name of Object.keys(examples))
    expect(container.querySelector(`section[data-component="${name}"]`)).not.toBeNull();
  expect(container.querySelector("[data-state-label]")).toBeNull();
});
it("opens a need from its card and withdraws with its keyboard action", () => {
  const { dispatch } = surface("NeedCard", examples.NeedCard?.[0]?.props ?? {});
  const card = screen.getByRole("button");
  fireEvent.click(card);
  expect(dispatch).toHaveBeenLastCalledWith(
    expect.objectContaining({ name: "need.open", context: { need_id: "n1" } }),
  );
  fireEvent.keyDown(card, { key: "Delete" });
  expect(dispatch).toHaveBeenLastCalledWith(
    expect.objectContaining({ name: "need.withdraw", context: { need_id: "n1" } }),
  );
  expect(screen.queryByText("Open")).toBeNull();
});
it("limits offer buttons to offers requesting a decision", () => {
  const { container, dispatch } = surface("OfferCard", examples.OfferCard?.[0]?.props ?? {});
  expect(screen.queryByRole("button")).toBeNull();
  expect(screen.getByText("€38")).toBeTruthy();
  expect(screen.getByText("18:00").getAttribute("datetime")).toBe("2030-06-05T18:00:00Z");
  fireEvent.keyDown(container.querySelector("[data-offer]") as HTMLElement, { key: "Delete" });
  expect(dispatch).toHaveBeenCalledWith(
    expect.objectContaining({ name: "offer.withdraw", context: { offer_id: "o1" } }),
  );
});
it.each([
  ["Accept", "offer.accept"],
  ["Ask", "offer.ask"],
])("sends %s through the catalog", (label, name) => {
  const { dispatch } = surface("OfferCard", examples.OfferCard?.[1]?.props ?? {});
  fireEvent.click(screen.getByRole("button", { name: label }));
  expect(dispatch).toHaveBeenCalledWith(
    expect.objectContaining({ name, context: { offer_id: "o2" } }),
  );
});
it("keeps answer choices and receipt provenance", () => {
  const { container } = surface("AnswerCard", examples.AnswerCard?.[2]?.props ?? {});
  expect(container.querySelectorAll(".chip")).toHaveLength(3);
  expect(container.querySelector(".chip-on")?.textContent).toBe("Mode 2 ✓");
});
it("does not invent a receipt for a literal boolean", () => {
  surface("AnswerCard", { kind: "bool", answer: false, query: "Ready?" });
  expect(screen.getByText("No")).toBeTruthy();
  expect(screen.queryByText(/#/)).toBeNull();
});
it("renders waiting metadata without claiming an answer", () => {
  const { container } = surface("AnswerCard", examples.AnswerCard?.[3]?.props ?? {});
  expect(container.querySelector('[data-state="waiting"]')).not.toBeNull();
  expect(screen.getByText(/waiting 4 min/)).toBeTruthy();
  expect(container.querySelector(".answer")).toBeNull();
});

it("groups the reference into 14 panels and nests objective bars in the plans", () => {
  const { container } = render(<Sheet06 />);
  expect(container.querySelectorAll("[data-panel]")).toHaveLength(14);
  expect(container.querySelector('[data-panel="ObjectiveBars"]')).toBeNull();
  expect(
    container.querySelectorAll('[data-panel="PlanCompare"] [data-component="ObjectiveBars"]'),
  ).toHaveLength(3);
  expect(container.querySelectorAll('[data-panel="TaskCard"] article')).toHaveLength(3);
});
it.each(["open", "negotiating", "proposed", "decided", "committed", "done", "withdrawn"])(
  "keeps the %s task state available through the catalog",
  (status) => {
    const { container } = surface("TaskCard", { ...examples.TaskCard?.[0]?.props, status });
    expect(container.querySelector("[data-fallback]")).toBeNull();
    expect(screen.getByRole("article", { name: new RegExp(`, ${status}$`) })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Mark done" }) !== null).toBe(
      status === "committed",
    );
  },
);
it("opens the drawn task title without an extra visible Open control", () => {
  const { dispatch } = surface("TaskCard", { ...examples.TaskCard?.[0]?.props, status: "decided" });
  expect(screen.queryByText("Open")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Open" }));
  expect(dispatch).toHaveBeenCalledWith(
    expect.objectContaining({ name: "task.open", context: { task_id: "t3" } }),
  );
});
it("opens a schedule task and keeps its date axis human readable", () => {
  const { container, dispatch } = surface("Gantt", examples.Gantt?.[0]?.props ?? {});
  expect(container.querySelector(".f06-axis")?.textContent).toContain("Thu 5 · today");
  fireEvent.click(screen.getByRole("button", { name: "Member A · done" }));
  expect(dispatch).toHaveBeenCalledWith(
    expect.objectContaining({ name: "task.open", context: { id: "t1" } }),
  );
});
it("explains supplied tradeoffs without sending a consent action", () => {
  const { dispatch } = surface("TensionCard", examples.TensionCard?.[0]?.props ?? {});
  fireEvent.click(screen.getByRole("button", { name: "Ask Gardener why" }));
  expect(screen.getByRole("status").textContent).toContain("Results Monday");
  expect(dispatch).not.toHaveBeenCalled();
  // The deadline shows its day and the viewer's local time; the machine value stays exact.
  const when = document.querySelector('time[datetime="2031-06-05T16:00:00Z"]');
  expect(when?.textContent).toMatch(/[A-Za-z]{2,}\.?,? \d{2}[:.]\d{2}/);
});
it("renders bound money with a total and names a breached charter cap", () => {
  const costs = surface("CostSplit", examples.CostSplit?.[0]?.props ?? {});
  expect(screen.getByText("€158")).toBeTruthy();
  costs.unmount();
  surface("FairnessMeter", {
    rows: [
      {
        participant: "p1",
        hours: { value: 12, event_ref: "e1" },
        share: { value: 60, event_ref: "e1" },
        rule: "rule 3",
      },
    ],
    cap: { value: 50, event_ref: "e1" },
  });
  expect(screen.getByText("Over cap: rule 3")).toBeTruthy();
});
