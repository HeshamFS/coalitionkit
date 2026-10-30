// SPDX-License-Identifier: Apache-2.0
import { A2uiSurface } from "@a2ui/react/v0_9";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { SurfaceBook } from "../../feed/surfaces";
import { examples } from "./examples";
import { sheetData } from "./sheet-data";

afterEach(cleanup);
it("edits a supplied initial goal and submits the edited draft only once", () => {
  const { container, dispatchAction } = mount("EntryComposer", { draft: "Initial goal" });
  expect(container.querySelector('[data-component="EntryComposer"]')).toHaveAttribute(
    "data-state",
    "typing",
  );
  const input = screen.getByRole("textbox", { name: "Your goal" });
  expect(input).toHaveValue("Initial goal");
  fireEvent.change(input, { target: { value: "Revised goal" } });
  const submit = screen.getByRole("button", { name: "Start a coalition" });
  fireEvent.click(submit);
  fireEvent.click(submit);
  expect(dispatchAction).toHaveBeenCalledTimes(1);
  expect(JSON.stringify(dispatchAction.mock.calls)).toContain('"goal":"Revised goal"');
  expect(submit).toBeDisabled();
});

it("shows the message coalition label as text", () => {
  mount("MessageDoor", { title: "Group P12" });
  expect(screen.getByText("CoalitionKit · Group P12")).toBeInTheDocument();
});

function mount(component: string, props: Record<string, unknown> = {}) {
  const dispatchAction = vi.fn();
  const book = new SurfaceBook(dispatchAction);
  book.apply("test", [
    { version: "v0.9", createSurface: { surfaceId: "test", catalogId: "coalitionkit/v0_9" } },
    {
      version: "v0.9",
      updateComponents: {
        surfaceId: "test",
        components: [{ id: "root", component, ...examples[component], ...props }],
      },
    },
  ]);
  const surface = book.list()[0];
  if (!surface || surface.fallback) throw new Error("Invalid family 02 example");
  return { ...render(<A2uiSurface surface={surface.model} />), dispatchAction };
}

it("returns from a selected compact detail to the list", () => {
  const { container, dispatchAction } = mount("SplitView", { detail: [] });
  expect(container.querySelector(".f02-split-frame")).toHaveAttribute("data-selected", "true");
  fireEvent.click(screen.getByRole("button", { name: "Back to list" }));
  expect(container.querySelector(".f02-split-frame")).toHaveAttribute("data-selected", "false");
  fireEvent.click(screen.getByRole("button", { name: "Task 2" }));
  expect(container.querySelector(".f02-split-frame")).toHaveAttribute("data-selected", "true");
  expect(JSON.stringify(dispatchAction.mock.calls)).toContain('"id":"t2"');
});

it("sends both single-decision controls through trusted review", () => {
  const { dispatchAction } = mount("ConsentTray");
  fireEvent.click(screen.getByRole("button", { name: "Read" }));
  fireEvent.click(screen.getByRole("button", { name: "Plan A · Review" }));
  const events = JSON.stringify(dispatchAction.mock.calls);
  expect(events).toContain('"name":"consent.open"');
  expect(events).toContain('"name":"open"');
  expect(events).toContain('"id":"p1"');
  expect(events).not.toContain('"signature"');
});

it("opens trusted charter review without signing locally", () => {
  const { dispatchAction } = mount("JoinScreen");
  fireEvent.click(screen.getByRole("button", { name: "Join with my agent" }));
  const events = JSON.stringify(dispatchAction.mock.calls);
  expect(events).toContain('"name":"charter.accept"');
  expect(events).toContain('"name":"open"');
  expect(events).not.toContain('"signature"');
});

it("does not copy an expired invitation", () => {
  const { dispatchAction } = mount("InviteCard", { expires: "2000-01-01T00:00:00Z" });
  const copy = screen.getByRole("button", { name: "Copy invite" });
  expect(copy).toBeDisabled();
  fireEvent.click(copy);
  expect(dispatchAction).not.toHaveBeenCalled();
});

it("dispatches revocation from an invitation the viewer can manage", () => {
  const invitation = { id: "invite:1", canRevoke: true };
  const { dispatchAction } = mount("InviteCard", { invitation });
  fireEvent.click(screen.getByRole("button", { name: "Revoke invitation" }));
  const events = JSON.stringify(dispatchAction.mock.calls);
  expect(events).toContain('"name":"invite.revoke"');
  expect(events).toContain('"id":"invite:1"');
});

it("marks notifications read and keeps their navigation references", () => {
  const { container, dispatchAction } = mount("NotificationCenter");
  fireEvent.click(screen.getByRole("button", { name: /Plan A needs your answer/ }));
  expect(JSON.stringify(dispatchAction.mock.calls)).toContain('"ref":"p1"');
  fireEvent.click(screen.getByRole("button", { name: "Mark all read" }));
  expect(container.querySelectorAll('[data-read="true"]')).toHaveLength(2);
  expect(container.querySelector(".f02-bell > span")).toBeNull();
});

it("requires confirmation before dispatching a spoken choice", () => {
  const { dispatchAction } = mount("VoiceTurn");
  fireEvent.click(screen.getByRole("button", { name: "first" }));
  expect(dispatchAction).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Confirm p1" }));
  expect(JSON.stringify(dispatchAction.mock.calls)).toContain('"value":"p1"');
});

it("never manufactures a signed confirmation from a local message reply", () => {
  const { dispatchAction } = mount("MessageDoor", { receipt: undefined });
  fireEvent.click(screen.getByRole("button", { name: "1 · Plan 1" }));
  expect(JSON.stringify(dispatchAction.mock.calls)).toContain('"value":"p1"');
  expect(screen.queryByText(/Signed with your key/)).toBeNull();
});

it("hides the previous host confirmation when a different message choice is sent", () => {
  mount("MessageDoor", sheetData.MessageDoor);
  expect(screen.getByText(/Signed with your key/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /2 · Split/ }));
  expect(screen.queryByText(/Signed with your key/)).toBeNull();
  expect(screen.queryByText(/receipt /)).toBeNull();
});

it("renders only supplied canvas activity with bound coordinates", () => {
  const { container } = mount("RoomShell", sheetData.RoomShell);
  expect(container.querySelector(".f02-activity-cursor")).toHaveTextContent("B's agent");
  expect(container.querySelector(".f02-activity-cursor")).toHaveStyle({
    left: "330px",
    top: "190px",
  });
  expect(container.querySelector(".f02-activity-link path")).toHaveAttribute(
    "d",
    "M150 128 C150 150, 170 150, 175 168",
  );
});
