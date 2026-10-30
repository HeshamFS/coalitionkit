// SPDX-License-Identifier: Apache-2.0
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Form } from "./form";
import { OfferForm } from "./offer";
import { DocumentShare, LimitField } from "./private-input";
import { ReviewStep } from "./review";

afterEach(cleanup);

it("excludes private field values from submitted values and schema display", () => {
  const send = vi.fn();
  const { container } = render(
    <Form
      p={{
        title: "Task",
        show_schema: true,
        fields: [
          { id: "title", label: "Title", kind: "text", initial: "Task 1" },
          {
            id: "limit",
            label: "Limit",
            kind: "money",
            private: "answer-only",
            initial: "secret",
            display_value: { value: 140, event_ref: "e1" },
          },
        ],
      }}
      send={send}
    />,
  );
  expect(container).not.toHaveTextContent("secret");
  fireEvent.click(screen.getByRole("button", { name: "Submit" }));
  expect(send).toHaveBeenCalledExactlyOnceWith("form.submit", { values: { title: "Task 1" } });
});

it("shows only explicitly shared limits, even if a private entry has a value", () => {
  const send = vi.fn();
  const { container } = render(
    <LimitField
      p={{
        limits: [
          { id: "private", label: "Limit", disclose: "answer-only", value: "secret" },
          { id: "shared", label: "Time", disclose: "shared" },
        ],
        shared_values: { private: "secret", shared: "10:00" },
      }}
      send={send}
    />,
  );
  expect(container).not.toHaveTextContent("secret");
  expect(screen.getByText("10:00")).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: /Limit/ }));
  expect(send).toHaveBeenCalledWith("limit.change", { id: "private" });
});

it("keeps masked preview fields hidden and shares only the document reference and masks", () => {
  const send = vi.fn();
  const masks = [{ field: "Owner", by: "agent" }];
  const { container } = render(
    <DocumentShare
      p={{
        document: "d1",
        masks,
        preview: { title: "Record", rows: [{ field: "Owner", value: "secret" }] },
      }}
      send={send}
    />,
  );
  expect(container).not.toHaveTextContent("secret");
  fireEvent.click(screen.getByRole("button", { name: "Share as evidence" }));
  expect(send).toHaveBeenCalledWith("evidence.share", { document: "d1", masks });
  fireEvent.click(screen.getByRole("button", { name: "Edit what's hidden" }));
  fireEvent.click(screen.getByRole("button", { name: "Remove mask" }));
  expect(container).not.toHaveTextContent("secret");
});

it("edits offer conditions and dispatches the edited cost with provenance", () => {
  const send = vi.fn();
  render(
    <OfferForm
      p={{
        what: "Resource",
        target: "need",
        cost: { kind: "estimate", amount: { value: 118, event_ref: "e1" } },
        conditions: ["After approval"],
      }}
      send={send}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "+ add" }));
  fireEvent.change(screen.getByRole("textbox", { name: "New condition" }), {
    target: { value: "Before noon" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Add" }));
  fireEvent.change(screen.getByRole("spinbutton"), { target: { value: "120" } });
  fireEvent.click(screen.getByRole("button", { name: "Offer" }));
  expect(send).toHaveBeenCalledWith(
    "coalition.offer",
    expect.objectContaining({
      conditions: ["After approval", "Before noon"],
      cost: { kind: "estimate", amount: { value: 120, event_ref: "e1" } },
    }),
  );
});

it("routes review editing and back separately and blocks a failed pre-check", () => {
  const send = vi.fn();
  render(
    <ReviewStep
      p={{
        sections: [{ label: "Goal", summary: "Task 1", editStep: "goal" }],
        precheck: { passed: false },
      }}
      send={send}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Edit" }));
  expect(send).toHaveBeenCalledWith("wizard.edit", { step: "goal" });
  fireEvent.click(screen.getByRole("button", { name: "Back" }));
  expect(send).toHaveBeenCalledWith("wizard.back");
  expect(screen.getByRole("button", { name: "Publish charter" })).toBeDisabled();
});
