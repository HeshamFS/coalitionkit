// SPDX-License-Identifier: Apache-2.0
import type { ComponentContext } from "@a2ui/web_core/v0_9";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { render as draw } from "./render";

afterEach(cleanup);
it("exports the selection and requires a separate confirmation to wipe", () => {
  const dispatchAction = vi.fn();
  const items = [
    { kind: "Log", included: true },
    { kind: "Answers", included: false },
  ];
  render(draw("ExportControl", { items }, { dispatchAction } as unknown as ComponentContext));
  fireEvent.click(screen.getByRole("checkbox", { name: "Log" }));
  fireEvent.click(screen.getByRole("checkbox", { name: "Answers" }));
  fireEvent.click(screen.getByRole("button", { name: "Download ZIP" }));
  expect(dispatchAction).toHaveBeenCalledWith({
    event: { name: "export.zip", context: { items: [{ kind: "Answers", included: true }] } },
  });
  dispatchAction.mockClear();
  fireEvent.click(screen.getByRole("button", { name: "Wipe my vault data" }));
  expect(dispatchAction).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
  expect(dispatchAction).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Wipe my vault data" }));
  fireEvent.click(screen.getByRole("button", { name: "Confirm wipe" }));
  expect(dispatchAction).toHaveBeenCalledWith({ event: { name: "vault.wipe", context: {} } });
});
it("hands off the exact subject and revision without signing", () => {
  const dispatchAction = vi.fn(),
    subject = { kind: "plan", id: "p1", revision: { value: 2, event_ref: "e1" } };
  render(
    draw("ChannelHandoff", { from: "lens", to: "phone", reason: "money", subject }, {
      dispatchAction,
    } as unknown as ComponentContext),
  );
  fireEvent.click(screen.getByRole("button", { name: "Open phone" }));
  expect(dispatchAction).toHaveBeenCalledExactlyOnceWith({
    event: { name: "handoff.open", context: { from: "lens", to: "phone", subject } },
  });
});
it("renders optional notification age without changing its deep link", () => {
  const dispatchAction = vi.fn();
  render(
    draw(
      "NotificationCard",
      { title: "Coalition 1", body: "Plan signed", ageLabel: "2 h", link: "/room/1" },
      { dispatchAction } as unknown as ComponentContext,
    ),
  );
  expect(screen.getByText("2 h")).toBeVisible();
  fireEvent.click(screen.getByRole("button"));
  expect(dispatchAction).toHaveBeenCalledWith({
    event: { name: "notification.open", context: { link: "/room/1" } },
  });
});
it("keeps a metric placeholder distinct from a measured value", () => {
  render(
    draw("MetricTile", { label: "Latency", placeholder: "[MS]", context: "target < 1 s" }, {
      dispatchAction: vi.fn(),
    } as unknown as ComponentContext),
  );
  expect(screen.getByText("[MS]")).toHaveAttribute("title", "Not run yet");
  expect(screen.getByText("target < 1 s")).toBeVisible();
});
it("hands off only after a completed hold and never emits a decision", () => {
  vi.useFakeTimers();
  try {
    const dispatchAction = vi.fn();
    const subject = { kind: "plan", id: "p1", revision: { value: 2, event_ref: "e1" } };
    render(
      draw("ChannelHandoff", { from: "lens", to: "phone", subject }, {
        dispatchAction,
      } as unknown as ComponentContext),
    );
    const button = screen.getByRole("button", { name: "Open phone" });
    fireEvent.pointerDown(button, { button: 0 });
    vi.advanceTimersByTime(300);
    fireEvent.pointerCancel(button);
    vi.advanceTimersByTime(600);
    expect(dispatchAction).not.toHaveBeenCalled();
    fireEvent.pointerDown(button, { button: 0 });
    vi.advanceTimersByTime(600);
    fireEvent.pointerUp(button);
    fireEvent.click(button, { detail: 1 });
    expect(dispatchAction).toHaveBeenCalledExactlyOnceWith({
      event: { name: "handoff.open", context: { subject, from: "lens", to: "phone" } },
    });
  } finally {
    vi.useRealTimers();
  }
});
