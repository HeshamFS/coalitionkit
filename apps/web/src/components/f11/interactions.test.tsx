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
