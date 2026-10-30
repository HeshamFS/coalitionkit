// SPDX-License-Identifier: Apache-2.0
import type { ComponentContext } from "@a2ui/web_core/v0_9";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { render as renderCatalog } from "./render";

afterEach(cleanup);
it("does not present an unfinished private match as a zero-result outcome", () => {
  render(
    renderCatalog("OverlapView", { mode: "intersection", parties: ["p1"], tokens: [] }, {
      dispatchAction: vi.fn(),
    } as unknown as ComponentContext),
  );
  expect(screen.getByRole("status").textContent).toContain("Matching");
  expect(screen.queryByText(/shared slot/)).toBeNull();
});
