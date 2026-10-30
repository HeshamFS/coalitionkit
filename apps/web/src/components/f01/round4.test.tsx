// SPDX-License-Identifier: Apache-2.0
import { cleanup, fireEvent, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { draw, event } from "./test-utils";

afterEach(cleanup);

it("Card keeps fields and provenance without an extra Open button", () => {
  const { dispatch } = draw("Card", {
    title: "Record",
    fields: [{ label: "Amount", value: { value: 12, event_ref: "e1" }, provenance: "measured" }],
  });
  expect(screen.getByText("Amount")).toBeTruthy();
  expect(screen.getByText("12")).toBeTruthy();
  expect(screen.getByText("measured")).toHaveClass("b-measured");
  expect(screen.queryByRole("button", { name: "Open" })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Record" }));
  event(dispatch, "open");
});

it("private fields hide bound values and stay read only", () => {
  draw(
    "TextField",
    { label: "Reference", private: true, help: "Stored in your vault", value: { path: "/value" } },
    { value: "secret-reference" },
  );
  expect(screen.getByRole("textbox")).toHaveValue("Kept in your vault");
  expect(screen.getByRole("textbox")).toHaveAttribute("readonly");
  expect(screen.getByRole("textbox")).toHaveAccessibleDescription("Stored in your vault");
  expect(screen.queryByDisplayValue("secret-reference")).toBeNull();
});

it("Button carries its tone and both icons through the catalog", () => {
  const { container, dispatch } = draw("Button", {
    label: "Continue",
    tone: "soft",
    icon: "plus",
    trailingIcon: "arrow",
    action: { name: "continue" },
  });
  expect(screen.getByRole("button")).toHaveClass("btn-soft");
  expect(container.querySelectorAll("button svg")).toHaveLength(2);
  fireEvent.click(screen.getByRole("button"));
  event(dispatch, "continue");
});

it.each(["CheckBox", "Switch"])("%s retains descriptions and disabled state", (name) => {
  const { dispatch } = draw(
    name,
    { label: "Share", description: "Only the hour", disabled: true, value: { path: "/value" } },
    { value: true },
  );
  const control = screen.getByRole(name === "Switch" ? "switch" : "checkbox");
  expect(control).toBeDisabled();
  expect(control).toBeChecked();
  expect(screen.getByText("Only the hour")).toBeTruthy();
  expect(dispatch).not.toHaveBeenCalled();
});

it("NumberField retains currency, helper text, and a zero maximum", () => {
  draw("NumberField", {
    label: "Amount",
    currency: "€",
    unit: "per unit",
    help: "Answer only",
    max: { value: 0, event_ref: "e1" },
  });
  expect(screen.getByText("€")).toBeTruthy();
  expect(screen.getByRole("spinbutton")).toHaveAttribute("max", "0");
  expect(screen.getByRole("spinbutton")).toHaveAccessibleDescription("Answer only");
});

it("TimeZone converts the shared instant and marks the next day", () => {
  draw("TimeZone", {
    value: "Europe/Lisbon",
    at: "2026-11-12T22:40:00Z",
    others: [
      { participant: "Member B", tz: "Europe/Berlin" },
      { participant: "Member C", tz: "Asia/Tokyo" },
    ],
  });
  expect(screen.getByText(/23:40/)).toBeTruthy();
  expect(screen.getByText(/07:40/)).toBeTruthy();
  expect(screen.getByText("tomorrow")).toBeTruthy();
});

it("Table keeps selection, redaction, bulk action and host pagination", () => {
  const { dispatch } = draw(
    "Table",
    {
      columns: [
        { key: "label", label: "Record" },
        { key: "value", label: "Value" },
      ],
      rows: { path: "/rows" },
      selection: "many",
      selected: ["r1"],
      total: { value: 12, event_ref: "e1" },
      pageSize: { value: 1, event_ref: "e1" },
      action: { label: "Add to plan" },
    },
    { rows: [{ id: "r1", label: "Record 1", value: { redacted: true } }] },
  );
  expect(screen.getByRole("img", { name: "Private value" })).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Add to plan" }));
  event(dispatch, "table.action", { ids: ["r1"] });
  fireEvent.click(screen.getByRole("button", { name: "Next page" }));
  event(dispatch, "table.page", { page: 2 });
  fireEvent.click(screen.getByLabelText("Select Record 1"));
  event(dispatch, "select", { ids: [] });
});

it("AudioPlayer displays bound timing and transcript and emits seek", () => {
  const { dispatch } = draw(
    "AudioPlayer",
    {
      duration: { value: 19, event_ref: "e1" },
      elapsed: { value: 7, event_ref: "e1" },
      transcript: { path: "/transcript" },
      waveform: [{ value: 0.5, event_ref: "e1" }],
    },
    { transcript: "A short note" },
  );
  expect(screen.getByText("0:07 / 0:19")).toBeTruthy();
  expect(screen.getByText("A short note")).toBeTruthy();
  fireEvent.change(screen.getByRole("slider"), { target: { value: "10" } });
  event(dispatch, "media.seek", { t: 10 });
});

it("FilterBar removes and clears filters without dropping the current query", () => {
  const { dispatch } = draw(
    "FilterBar",
    { query: { path: "/query" }, filters: [{ field: "Status", op: "is", value: "Open" }] },
    { query: "record" },
  );
  fireEvent.click(screen.getByRole("button", { name: "Remove Status filter" }));
  event(dispatch, "filter.change", { query: "record", filters: [] });
  fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));
  event(dispatch, "filter.change", { query: "", filters: [] });
});

it("DateTimeInput range disables busy days and emits a complete range", () => {
  const { dispatch } = draw(
    "DateTimeInput",
    {
      range: true,
      busy: ["2026-11-10"],
      min: "2026-11-01",
      max: "2026-11-30",
      value: { path: "/dates" },
    },
    { dates: ["2026-11-12", "2026-11-14"] },
  );
  fireEvent.click(screen.getByRole("button"));
  expect(screen.getByRole("button", { name: "2026-11-10" })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "2026-11-17" }));
  expect(dispatch).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "2026-11-19" }));
  event(dispatch, "change", { value: ["2026-11-17", "2026-11-19"] });
  expect(screen.queryByRole("dialog")).toBeNull();
});
