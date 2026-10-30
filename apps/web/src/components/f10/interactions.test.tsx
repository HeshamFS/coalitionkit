// SPDX-License-Identifier: Apache-2.0
import type { ComponentContext } from "@a2ui/web_core/v0_9";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { PreviewState } from "../f08/shared";
import { render as draw } from "./render";

afterEach(cleanup);
it("stops a recording with the original vault references", () => {
  const dispatchAction = vi.fn();
  const props = { video: "vault:1", narration: "vault:2", masks: [] };
  render(
    <PreviewState value="recording">
      {draw("CaptureCard", props, { dispatchAction } as unknown as ComponentContext)}
    </PreviewState>,
  );
  fireEvent.click(screen.getByRole("button", { name: "Stop recording" }));
  expect(dispatchAction).toHaveBeenCalledWith({
    event: { name: "capture.stop", context: { video: "vault:1", narration: "vault:2" } },
  });
  expect(screen.getByRole("button", { name: "Recorded" })).toBeDisabled();
});
it("exposes chart values in a table and preserves the export source", () => {
  const dispatchAction = vi.fn();
  render(
    draw(
      "DeviceReading",
      {
        source: "device:1",
        unit: "units",
        series: [
          {
            t: "10:00",
            value: { value: 42, event_ref: "e1" },
            confidence: { value: 0.9, event_ref: "e1" },
          },
        ],
      },
      { dispatchAction } as unknown as ComponentContext,
    ),
  );
  fireEvent.click(screen.getByRole("button", { name: "table view" }));
  expect(screen.getByRole("cell", { name: "42" })).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Export CSV" }));
  expect(dispatchAction).toHaveBeenCalledWith({
    event: { name: "reading.export", context: { source: "device:1" } },
  });
  fireEvent.click(screen.getByRole("button", { name: "chart view" }));
  expect(screen.getByRole("img")).toBeVisible();
});
