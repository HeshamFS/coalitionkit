// SPDX-License-Identifier: Apache-2.0
import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { roomFixture } from "./fixture";
import { Decisions, Metrics, Participants, Plans, Privacy, Schedule, Wiring } from "./parts";

it("renders room parts from the viewer projection and routes requests to trusted UI", () => {
  const open = vi.fn();
  render(
    <>
      <Participants state={roomFixture} />
      <Plans state={roomFixture} />
      <Metrics state={roomFixture} />
      <Wiring state={roomFixture} />
      <Decisions
        state={roomFixture}
        requests={[
          {
            id: "r1",
            kind: "plan",
            subjectId: "plan-1",
            revision: 1,
            message: "Review this option",
          },
        ]}
        onOpen={open}
      />
      <Privacy state={roomFixture} />
      <Schedule state={roomFixture} />
    </>,
  );
  expect(screen.getByText("Member A")).toBeInTheDocument();
  expect(screen.getByText("Agent A on Vendor A")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Accept A", hidden: true })).toBeDisabled();
  for (const name of [
    "Plan options for Coordinate the next step",
    "Metrics",
    "Wiring · live",
    "Decisions",
    "What stayed private",
  ])
    expect(screen.getByLabelText(name)).toBeInTheDocument();
  expect(screen.getByText("Private notes")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /Review plan A/ }));
  expect(open).toHaveBeenCalledWith("r1");
});
it("never substitutes another member for an unknown viewer", () => {
  render(<Participants state={{ ...roomFixture, viewer: undefined }} own />);
  expect(screen.queryByText("Member A")).not.toBeInTheDocument();
  expect(screen.getByText("Your part is not in this projection yet.")).toBeInTheDocument();
});
