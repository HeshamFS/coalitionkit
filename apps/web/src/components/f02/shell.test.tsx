// SPDX-License-Identifier: Apache-2.0
import { A2uiSurface } from "@a2ui/react/v0_9";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { SurfaceBook } from "../../feed/surfaces";
import { examples } from "./examples";

afterEach(cleanup);
it("keeps standalone TopBar display-only as the catalog requires", () => {
  mount("TopBar");
  expect(screen.queryByRole("button")).toBeNull();
});

function mount(component: string, props: Record<string, unknown> = {}) {
  const dispatchAction = vi.fn();
  const book = new SurfaceBook(dispatchAction);
  book.apply("shell", [
    { version: "v0.9", createSurface: { surfaceId: "shell", catalogId: "coalitionkit/v0_9" } },
    {
      version: "v0.9",
      updateComponents: {
        surfaceId: "shell",
        components: [{ id: "root", component, ...examples[component], ...props }],
      },
    },
    {
      version: "v0.9",
      updateDataModel: { surfaceId: "shell", path: "/", value: { stage: "Decide" } },
    },
  ]);
  const surface = book.list()[0];
  if (!surface || surface.fallback) throw new Error("Invalid shell surface");
  const result = render(<A2uiSurface surface={surface.model} />);
  return { ...result, dispatchAction };
}

it("keeps shell actions in the header and resolves the stage binding", () => {
  const { container, dispatchAction } = mount("RoomShell");
  expect(container.querySelector('[aria-current="step"]')).toHaveTextContent("Decide");
  const invite = screen.getByRole("button", { name: "Invite" });
  expect(invite.closest("header")).not.toBeNull();
  fireEvent.click(invite);
  expect(JSON.stringify(dispatchAction.mock.calls)).toContain('"name":"invite.open"');
  fireEvent.click(screen.getByRole("button", { name: "Search" }));
  expect(JSON.stringify(dispatchAction.mock.calls)).toContain('"name":"search.open"');
});

it("keeps the selected phone tab and dispatches its id", () => {
  const { dispatchAction } = mount("PhoneShell", { header: undefined, stack: [] });
  const plans = screen.getByRole("button", { name: "Plans" });
  fireEvent.click(plans);
  expect(plans).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByRole("button", { name: "Now" })).toHaveAttribute("aria-pressed", "false");
  expect(JSON.stringify(dispatchAction.mock.calls)).toContain('"id":"Plans"');
});

it("submits private chat text once and clears the composer", () => {
  const { dispatchAction } = mount("AgentDock");
  const input = screen.getByRole("textbox", { name: "Message your agent" });
  const send = screen.getByRole("button", { name: "Send" });
  expect(send).toBeDisabled();
  fireEvent.change(input, { target: { value: "Review my options" } });
  fireEvent.click(send);
  expect(JSON.stringify(dispatchAction.mock.calls)).toContain('"text":"Review my options"');
  expect(input).toHaveValue("");
  expect(send).toBeDisabled();
});

it("sorts pending requests by deadline and sends the subject for trusted review", () => {
  const subject = { kind: "plan", id: "p1", revision: { value: 2, event_ref: "event:2" } };
  const { container, dispatchAction } = mount("ConsentTray", {
    requests: [
      { kind: "charter", label: "Charter", subject: { ...subject, id: "c1" } },
      { kind: "plan", label: "Plan A", subject, deadline: "2099-01-01T10:00:00Z" },
    ],
  });
  expect(container.querySelector(".f02-tray-request")).toHaveTextContent("Plan A");
  fireEvent.click(screen.getByRole("button", { name: "Plan A · Review" }));
  const events = JSON.stringify(dispatchAction.mock.calls);
  expect(events).toContain('"name":"consent.open"');
  expect(events).toContain('"name":"open"');
  expect(events).toContain('"id":"p1"');
  expect(events).not.toContain('"signature"');
});
