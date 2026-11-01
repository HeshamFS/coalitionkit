// SPDX-License-Identifier: Apache-2.0
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { fieldsOf, type JsonSchema, toExt, validate } from "./extSchema";
import { SchemaForm } from "./schemaForm";

const schema: JsonSchema = {
  type: "object",
  required: ["label", "level"],
  properties: {
    label: { type: "string", title: "Label", description: "A short name", pattern: "^[a-z]+$" },
    level: { type: "string", title: "Level", enum: ["low", "high"] },
    count: { type: "integer", title: "Count", minimum: 1, maximum: 5 },
    ready: { type: "boolean", title: "Ready" },
    secret: { type: "string", title: "Secret note", "x-private": true },
  },
};

describe("SchemaForm", () => {
  it("draws labels from the schema, marks required fields and renders an enum as a select", () => {
    render(<SchemaForm schema={schema} onSubmit={() => {}} />);
    expect(screen.getByLabelText(/^Label \*/)).toBeTruthy();
    const level = screen.getByLabelText(/^Level \*/);
    expect(level.tagName).toBe("SELECT");
    expect(screen.getByRole("option", { name: "high" })).toBeTruthy();
    expect(screen.getByText("A short name")).toBeTruthy();
    expect(screen.getByLabelText("Ready").getAttribute("type")).toBe("checkbox");
  });

  it("blocks submit with a message while a required field is missing", async () => {
    const onSubmit = vi.fn();
    render(<SchemaForm schema={schema} onSubmit={onSubmit} />);
    await userEvent.click(screen.getByRole("button", { name: "Add to my offer" }));
    const alert = screen.getByRole("alert");
    expect(alert.textContent).toContain("Label is required");
    expect(alert.textContent).toContain("Level is required");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("checks pattern and range before sending", async () => {
    const onSubmit = vi.fn();
    render(<SchemaForm schema={schema} onSubmit={onSubmit} />);
    await userEvent.type(screen.getByLabelText(/^Label/), "BAD1");
    await userEvent.selectOptions(screen.getByLabelText(/^Level/), "low");
    await userEvent.type(screen.getByLabelText("Count"), "9");
    await userEvent.click(screen.getByRole("button", { name: "Add to my offer" }));
    const alert = screen.getByRole("alert");
    expect(alert.textContent).toContain("Label does not match");
    expect(alert.textContent).toContain("Count must be at most 5");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("sends typed values and never a private field in the public body", async () => {
    const onSubmit = vi.fn();
    render(<SchemaForm schema={schema} onSubmit={onSubmit} />);
    expect(screen.getByLabelText(/^Secret note/).hasAttribute("disabled")).toBe(true);
    await userEvent.type(screen.getByLabelText(/^Label/), "alpha");
    await userEvent.selectOptions(screen.getByLabelText(/^Level/), "high");
    await userEvent.type(screen.getByLabelText("Count"), "3");
    await userEvent.click(screen.getByRole("button", { name: "Add to my offer" }));
    expect(onSubmit).toHaveBeenCalledTimes(1);
    const ext = onSubmit.mock.calls[0]?.[0] as Record<string, unknown>;
    expect(ext).toEqual({ label: "alpha", level: "high", count: 3 });
    expect(Object.keys(ext)).not.toContain("secret");
  });
});

describe("schema edge cases from the review", () => {
  it("renders a field defined through a local $ref", () => {
    const fields = fieldsOf({
      type: "object",
      required: ["count"],
      properties: { count: { $ref: "#/$defs/count" } },
      $defs: { count: { type: "integer", title: "Count", minimum: 1 } },
    });
    expect(fields.map((f) => [f.key, f.kind, f.required, f.title])).toEqual([
      ["count", "number", true, "Count"],
    ]);
  });
  it("accepts a required false and keeps an optional false", () => {
    const fields = fieldsOf({
      type: "object",
      required: ["enabled"],
      properties: { enabled: { type: "boolean" }, extra: { type: "boolean" } },
    });
    expect(validate(fields, { enabled: false })).toEqual({});
    expect(toExt(fields, { enabled: false, extra: false })).toEqual({
      enabled: false,
      extra: false,
    });
    expect(toExt(fields, {})).toEqual({ enabled: false });
  });
});
