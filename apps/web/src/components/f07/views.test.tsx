// SPDX-License-Identifier: Apache-2.0
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { One } from "../../gallery/Drawn";

afterEach(cleanup);

it("formats arrival timestamps while preserving the machine-readable value", () => {
  const arrivedAt = "2030-06-05T22:58:00Z";
  const { container } = render(
    <One component="ArrivalCard" props={{ arrivedAt, place: "Place 1", others: [] }} />,
  );
  expect(container.querySelector("[data-fallback]")).toBeNull();
  expect(screen.getByText("22:58")).toHaveAttribute("dateTime", arrivedAt);
  expect(container.textContent).not.toContain(arrivedAt);
});

it("formats route timestamps and retains the route state", () => {
  const eta = "2030-06-05T22:58:00Z";
  const { container } = render(
    <One component="RouteCard" props={{ eta, progress: { value: 0.35, event_ref: "e1" } }} />,
  );
  expect(screen.getByText("22:58")).toHaveAttribute("dateTime", eta);
  expect(container.querySelector('section[data-state="moving"]')).not.toBeNull();
});

it("keeps unbadged upcoming agenda items and their action accessible", () => {
  render(
    <One
      component="AgendaList"
      props={{
        day: "2030-06-05",
        items: [{ time: "16:00", title: "Task 1", state: "next", action: "Join" }],
      }}
    />,
  );
  expect(screen.getByRole("button", { name: "Join" })).toBeVisible();
  expect(screen.queryByText("next")).toBeNull();
});
