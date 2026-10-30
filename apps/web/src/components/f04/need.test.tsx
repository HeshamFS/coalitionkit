// SPDX-License-Identifier: Apache-2.0
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { NeedForm } from "./need";

afterEach(cleanup);

it("publishes the edited deadline, quantity and audience with the need", () => {
  const send = vi.fn();
  render(
    <NeedForm
      p={{
        text: "Resource 1",
        quantity: { value: 2, event_ref: "e1" },
        constraints: [
          { kind: "deadline", value: "01:00" },
          { kind: "condition", value: "ready" },
        ],
        audience: "coalition",
      }}
      send={send}
    />,
  );
  fireEvent.change(screen.getByLabelText("By"), { target: { value: "02:00" } });
  fireEvent.click(screen.getByRole("button", { name: "Increase quantity" }));
  fireEvent.click(screen.getByRole("button", { name: "Host only" }));
  fireEvent.click(screen.getByRole("button", { name: "Publish need" }));
  expect(send).toHaveBeenCalledExactlyOnceWith("coalition.need", {
    text: "Resource 1",
    quantity: { value: 3, event_ref: "e1" },
    audience: "me",
    constraints: [
      { kind: "condition", value: "ready" },
      { kind: "deadline", value: "02:00" },
    ],
  });
  expect(screen.getByRole("button", { name: "Publish need" })).toBeDisabled();
});
