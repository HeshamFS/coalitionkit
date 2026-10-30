// SPDX-License-Identifier: Apache-2.0
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { AvailabilityGrid } from "./availability";
import { examples } from "./examples";

afterEach(cleanup);

it("renders the full week and toggles only the selected slot", () => {
  const send = vi.fn();
  render(<AvailabilityGrid p={examples.AvailabilityGrid ?? {}} send={send} />);
  expect(screen.getAllByRole("button", { pressed: true })).toHaveLength(14);
  const slot = screen.getByRole("button", { name: "Wed 09:00" });
  fireEvent.click(slot);
  expect(slot).toHaveAttribute("aria-pressed", "true");
  expect(send).toHaveBeenLastCalledWith("availability.paint", {
    day: "Wed",
    slot: "Wed09:00",
    available: true,
  });
  fireEvent.click(slot);
  expect(slot).toHaveAttribute("aria-pressed", "false");
  expect(send).toHaveBeenLastCalledWith("availability.paint", {
    day: "Wed",
    slot: "Wed09:00",
    available: false,
  });
  expect(screen.getByRole("button", { name: "Mon 09:00" })).toHaveAttribute("aria-pressed", "true");
});

it("requests a calendar import without claiming an import succeeded", () => {
  const send = vi.fn();
  const { container } = render(
    <AvailabilityGrid p={{ days: [], slots: [], source: "manual" }} send={send} />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Import calendar" }));
  expect(send).toHaveBeenCalledExactlyOnceWith("availability.import");
  expect(container.querySelector("section")).toHaveAttribute("data-state", "empty");
});
