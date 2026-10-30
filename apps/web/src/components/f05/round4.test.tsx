// SPDX-License-Identifier: Apache-2.0
import { A2uiSurface } from "@a2ui/react/v0_9";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { SurfaceBook } from "../../feed/surfaces";
import { One } from "../../gallery/Drawn";

afterEach(cleanup);

function surface(component: string, props: Record<string, unknown>) {
  const dispatch = vi.fn();
  const book = new SurfaceBook(dispatch);
  book.apply("r4", [
    { version: "v0.9", createSurface: { surfaceId: "r4", catalogId: "coalitionkit/v0_9" } },
    {
      version: "v0.9",
      updateComponents: { surfaceId: "r4", components: [{ id: "root", component, ...props }] },
    },
  ]);
  const entry = book.list()[0];
  if (!entry || entry.fallback) throw new Error("Catalog surface failed");
  render(<A2uiSurface surface={entry.model} />);
  return dispatch;
}

it("shows the next idle reading with its original timestamp", () => {
  const timestamp = "2030-06-05T12:30:00Z";
  render(<One component="AgentPresence" props={{ state: "idle", nextReadingAt: timestamp }} />);
  expect(screen.getByText("12:30")).toHaveAttribute("dateTime", timestamp);
});

it("dispatches a role-change request for the joined participant", () => {
  const dispatch = surface("InviteList", { invitations: [{ participant: "p1", state: "joined" }] });
  fireEvent.click(screen.getByRole("button", { name: "Change role" }));
  expect(dispatch).toHaveBeenCalledWith(
    expect.objectContaining({
      name: "invite.changeRole",
      context: { participant: "p1" },
    }),
  );
});

it("displays a bound per-member cost and preserves zero estimates", () => {
  render(
    <One
      component="RouteCard"
      props={{
        participants: ["p1"],
        costPerMember: { value: 0, event_ref: "e1" },
        currency: "EUR",
      }}
    />,
  );
  expect(screen.getByText("1 members · ≈ €0 each")).toBeVisible();
});

it("dispatches bounded pin adjustments using the keyboard, then confirms the reference", () => {
  const dispatch = surface("PlacePicker", {
    results: [{ place: "p1" }],
    pin: {
      ref: "p1",
      x: { value: 265, event_ref: "e1" },
      y: { value: 96, event_ref: "e1" },
    },
  });
  fireEvent.keyDown(screen.getByRole("button", { name: "Adjust p1 pin" }), { key: "ArrowRight" });
  expect(dispatch).toHaveBeenCalledWith(
    expect.objectContaining({
      name: "place.adjust",
      context: { ref: "p1", x: 266, y: 96 },
    }),
  );
  fireEvent.click(screen.getByRole("button", { name: "Use this place" }));
  expect(dispatch).toHaveBeenLastCalledWith(
    expect.objectContaining({
      name: "place.pick",
      context: { ref: "p1" },
    }),
  );
});
