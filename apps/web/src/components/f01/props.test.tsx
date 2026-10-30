// SPDX-License-Identifier: Apache-2.0
import { cleanup, fireEvent, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { draw, event } from "./test-utils";

afterEach(cleanup);

it("Slider retains both range endpoints and prevents crossing", () => {
  const { dispatch } = draw(
    "Slider",
    { value: { path: "/range" }, unit: "%" },
    { range: [20, 70] },
  );
  expect(screen.getAllByRole("slider")).toHaveLength(2);
  fireEvent.change(screen.getByLabelText("Lower value"), { target: { value: "40" } });
  event(dispatch, "change", { value: [40, 70], unit: "%" });
  fireEvent.change(screen.getByLabelText("Upper value"), { target: { value: "10" } });
  event(dispatch, "change", { value: [40, 40], unit: "%" });
});

it.each(["Text", "Progress", "Meter", "Skeleton"])(
  "%s keeps provenance in its catalog rendering",
  (name) => {
    draw(
      name,
      {
        text: "Value",
        label: "Value",
        value: { value: 42, event_ref: "e1" },
        state: "filled",
        previous: { path: "/previous" },
        provenance: "measured",
      },
      { previous: "Earlier" },
    );
    expect(screen.getByText("measured")).toHaveClass("b-measured");
  },
);
it("Banner does not invent controls when no action was supplied", () => {
  draw("Banner", { title: "Everyone agreed.", body: "The plan is signed.", tone: "agreed" });
  expect(screen.queryByRole("button")).toBeNull();
});
it("TextArea counts the bound text and preserves the maximum", () => {
  draw(
    "TextArea",
    { label: "Note", value: { path: "/text" }, maxLength: { value: 20, event_ref: "e1" } },
    { text: "Ready" },
  );
  expect(screen.getByRole("textbox")).toHaveAttribute("maxlength", "20");
  expect(screen.getByText("5 / 20")).toBeTruthy();
  fireEvent.change(screen.getByRole("textbox"), { target: { value: "Ready now" } });
  expect(screen.getByText("9 / 20")).toBeTruthy();
});
it("NumberField steppers honor bounds and emit numeric changes", () => {
  const { dispatch } = draw(
    "NumberField",
    {
      label: "Units",
      value: { path: "/amount" },
      min: { value: 0, event_ref: "e1" },
      max: { value: 4, event_ref: "e1" },
      step: { value: 2, event_ref: "e1" },
    },
    { amount: 2 },
  );
  fireEvent.click(screen.getByLabelText("Increase Units"));
  event(dispatch, "change", { value: 4 });
  expect(screen.getByLabelText("Increase Units")).toBeDisabled();
  fireEvent.click(screen.getByLabelText("Decrease Units"));
  fireEvent.click(screen.getByLabelText("Decrease Units"));
  event(dispatch, "change", { value: 0 });
  expect(screen.getByLabelText("Decrease Units")).toBeDisabled();
});
it("SearchField keeps group headings and metadata while picking the result id", () => {
  const { dispatch } = draw("SearchField", {
    groups: [
      {
        label: "Offers",
        items: [{ id: "o1", label: "Resource 1", hint: "Offer", icon: "resource" }],
      },
    ],
  });
  expect(screen.getByText("Offers")).toBeTruthy();
  expect(screen.getByText("Offer")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Resource 1 Offer" }));
  event(dispatch, "search.pick", { id: "o1" });
});
it("FileDrop renders upload state from its host binding", () => {
  draw(
    "FileDrop",
    { target: { path: "/files" } },
    { files: [{ id: "f1", name: "record.pdf", progress: { value: 72, event_ref: "e1" } }] },
  );
  expect(screen.getByRole("progressbar", { name: "record.pdf" })).toHaveAttribute(
    "aria-valuenow",
    "72",
  );
});
it("List renders its catalog template", () => {
  draw("List", { items: { path: "/items" }, template: "item" }, { items: [{ id: "a" }] }, [
    { id: "item", component: "Text", text: "Template content" },
  ]);
  expect(screen.getByText("Template content")).toBeTruthy();
});

it("ChoicePicker keeps multiple selections and disabled options", () => {
  const { dispatch } = draw(
    "ChoicePicker",
    {
      multiple: true,
      value: { path: "/selected" },
      options: [
        { id: "a", label: "First" },
        { id: "b", label: "Second" },
        { id: "c", label: "Unavailable", disabled: true },
      ],
    },
    { selected: ["a"] },
  );
  fireEvent.click(screen.getByRole("combobox"));
  expect(screen.getByRole("option", { name: "Unavailable" })).toBeDisabled();
  fireEvent.click(screen.getByRole("option", { name: "Second" }));
  event(dispatch, "select", { value: ["a", "b"] });
  fireEvent.click(screen.getByLabelText("Remove First"));
  event(dispatch, "select", { value: ["b"] });
  fireEvent.keyDown(screen.getByRole("combobox"), { key: "Escape" });
  expect(screen.queryByRole("listbox")).toBeNull();
});
