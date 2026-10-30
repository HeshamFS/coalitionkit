// SPDX-License-Identifier: Apache-2.0
import type { ComponentContext } from "@a2ui/web_core/v0_9";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Sheet10 } from "../../gallery/sheets/Sheet10";
import { examples } from "./examples";
import { render as draw } from "./render";

afterEach(cleanup);
it("renders all family 10 panels through the catalog", () => {
  const { container } = render(<Sheet10 />);
  expect(container.querySelector("[data-fallback]")).toBeNull();
  expect(container.querySelectorAll("[data-panel]")).toHaveLength(9);
  for (const example of examples)
    expect(container.querySelector(`section[data-component="${example.name}"]`)).not.toBeNull();
});
it("summarizes every test while showing failures and running tests", () => {
  const dispatchAction = vi.fn();
  const props = examples.find((e) => e.name === "AttackTests")?.states[0]?.props ?? {};
  const { container } = render(
    draw("AttackTests", props, { dispatchAction } as unknown as ComponentContext),
  );
  expect(screen.getByText("12 / 14 pass · 1 fail · 1 running")).toBeVisible();
  expect(container.querySelectorAll(".f10-tests li")).toHaveLength(5);
  expect(screen.getByText("fail")).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Fix and re-run" }));
  expect(dispatchAction).toHaveBeenCalledWith({ event: { name: "tests.rerun", context: {} } });
});
