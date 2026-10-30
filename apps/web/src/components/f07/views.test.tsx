// SPDX-License-Identifier: Apache-2.0
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { One } from "../../gallery/Drawn";

afterEach(cleanup);

it("aligns working hours across zones and splits a range across midnight", () => {
  const bound = (value: number) => ({ value, event_ref: "e1" });
  const { container } = render(
    <One
      component="TimeZoneStrip"
      props={{
        now: "2030-06-05T09:20:00Z",
        people: [
          { participant: "p1", tz: "UTC", workingHours: [{ start: bound(8), end: bound(18) }] },
          {
            participant: "p2",
            tz: "Asia/Tokyo",
            workingHours: [{ start: bound(8), end: bound(18) }],
          },
        ],
      }}
    />,
  );
  expect(screen.getByText("09:20")).toBeVisible();
  expect(screen.getByText("18:20")).toBeVisible();
  const tracks = container.querySelectorAll(".f07-zonebar");
  expect(tracks[1]?.querySelectorAll("span")).toHaveLength(2);
  expect(tracks[1]?.querySelector("i")?.style.left).toBe(tracks[0]?.querySelector("i")?.style.left);
});

it("does not draw invalid time-zone coordinates", () => {
  const { container } = render(
    <One
      component="TimeZoneStrip"
      props={{
        now: "invalid",
        people: [
          {
            participant: "p1",
            tz: "invalid",
            workingHours: [
              { start: { value: 0, event_ref: "e1" }, end: { value: 24, event_ref: "e1" } },
            ],
          },
        ],
      }}
    />,
  );
  expect(screen.getByText("—")).toBeVisible();
  expect(container.querySelectorAll(".f07-zonebar span, .f07-zonebar i")).toHaveLength(0);
});

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
