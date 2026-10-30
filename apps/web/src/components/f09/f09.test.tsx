// SPDX-License-Identifier: Apache-2.0
import type { ComponentContext } from "@a2ui/web_core/v0_9";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Sheet09 } from "../../gallery/sheets/Sheet09";
import { examples } from "./examples";
import { render as renderCatalog } from "./render";
import { bound, sheetSamples } from "./sheetSamples";

afterEach(cleanup);
function mount(name: string, props = sheetSamples[name] ?? {}) {
  const dispatchAction = vi.fn();
  const view = render(
    renderCatalog(name, props, { dispatchAction } as unknown as ComponentContext),
  );
  return { ...view, dispatchAction };
}
it("renders all 18 components in the 14 reference panels through the catalog", () => {
  const { container } = render(<Sheet09 />);
  expect(container.querySelector("[data-fallback]")).toBeNull();
  expect(container.querySelectorAll("[data-panel]")).toHaveLength(14);
  for (const example of examples)
    expect(
      container.querySelector(`[data-component="${example.name}"]`),
      example.name,
    ).not.toBeNull();
  expect(container.querySelectorAll('[data-component="ErrorNotice"]')).toHaveLength(6);
  expect(container.querySelectorAll('[data-component="ConnectionStatus"]')).toHaveLength(3);
});
const cases = [
  { name: "ActivityStream", button: /log entry 56/, event: "item.open", data: { seq: bound(56) } },
  { name: "ChainView", button: /Verify chain/, event: "chain.verify", data: {} },
  {
    name: "EvidenceCard",
    button: /Open evidence/,
    event: "evidence.open",
    data: { ref: "ev-7Q2 · #31" },
  },
  { name: "LiveDocks", button: /decision waits/, event: "dock.open", data: { ref: "decisions" } },
  { name: "LogStream", button: /51.*11:40/, event: "entry.open", data: { seq: bound(51) } },
  { name: "RippleBanner", button: /What changed/, event: "ripple.open", data: {} },
  {
    name: "StewardVerdict",
    button: /Verify signature/,
    event: "verdict.verify",
    data: { verdict: sheetSamples.StewardVerdict?.verdict },
  },
  {
    name: "VerifyPanel",
    button: /Run verification/,
    event: "verify.run",
    data: { export: sheetSamples.VerifyPanel?.export },
  },
  {
    name: "VerifyPanel",
    button: /Download log/,
    event: "log.download",
    data: { export: sheetSamples.VerifyPanel?.export },
  },
];
describe("family 09 actions", () => {
  it.each(cases)(
    "$name sends $event with its bound references",
    ({ name, button, event, data }) => {
      const { dispatchAction } = mount(name);
      fireEvent.click(screen.getByRole("button", { name: button }));
      expect(dispatchAction).toHaveBeenCalledWith({ event: { name: event, context: data } });
    },
  );
  it("reconnects with the current run", () => {
    const { dispatchAction } = mount("ConnectionStatus", { feed: "offline", run: "r2" });
    fireEvent.click(screen.getByRole("button", { name: "Reconnect" }));
    expect(dispatchAction).toHaveBeenCalledWith({
      event: { name: "feed.reconnect", context: { run: "r2" } },
    });
  });
  it("verifies a receipt without losing its event reference", () => {
    const { dispatchAction } = mount("ReceiptBadge", { seq: bound(54), state: "ok" });
    fireEvent.click(screen.getByRole("button"));
    expect(dispatchAction).toHaveBeenCalledWith({
      event: { name: "receipt.verify", context: { seq: bound(54) } },
    });
  });
  it("opens a standalone event", () => {
    const { dispatchAction } = mount("EventRow", {
      seq: bound(54),
      summary: "Decision recorded",
      form: "original",
    });
    fireEvent.click(screen.getByRole("button"));
    expect(dispatchAction).toHaveBeenCalledWith({
      event: { name: "entry.open", context: { seq: bound(54) } },
    });
  });
  it("shows retry only when explicitly available", () => {
    const { dispatchAction, rerender } = mount("ErrorNotice", {
      code: "stale_subject",
      ref: "e1",
      detail: { retry: true },
    });
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(dispatchAction).toHaveBeenCalledWith({
      event: { name: "error.retry", context: { code: "stale_subject", ref: "e1" } },
    });
    rerender(
      renderCatalog("ErrorNotice", { code: "stale_subject" }, {
        dispatchAction,
      } as unknown as ComponentContext),
    );
    expect(screen.queryByRole("button")).toBeNull();
  });
  it("edits a mask label after opening the owner control", () => {
    const { dispatchAction } = mount("MediaWithMasks");
    fireEvent.click(screen.getByRole("button", { name: "+ label" }));
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "Region A" } });
    fireEvent.blur(screen.getByRole("textbox"));
    expect(dispatchAction).toHaveBeenCalledWith({
      event: { name: "mask.label", context: { id: "m1", label: "Region A" } },
    });
  });
  it("filters activity without emitting a log action", () => {
    const { dispatchAction } = mount("ActivityStream");
    fireEvent.click(screen.getByRole("button", { name: "Decisions" }));
    expect(screen.queryByText("changed")).toBeNull();
    expect(screen.getByRole("button", { name: /log entry 52/ })).toBeVisible();
    expect(dispatchAction).not.toHaveBeenCalled();
  });
});
