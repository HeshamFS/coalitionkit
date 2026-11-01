// SPDX-License-Identifier: Apache-2.0
import { expect, it } from "vitest";
import { fieldsOf, type JsonSchema, toExt } from "./extSchema";
import allOfJson from "./fixtures/bundled-allof.json";
import offer from "./fixtures/bundled-offer.json";
import { publicSchema } from "./offerPanel";

const allOf = allOfJson as unknown as JsonSchema;

it("renders the server's bundled sibling property with its required and private annotations", () => {
  const fields = fieldsOf(offer);
  expect(fields).toHaveLength(1);
  expect(fields[0]).toMatchObject({
    key: "count",
    kind: "number",
    required: true,
    private: true,
    schema: { type: "integer", "x-private": true },
  });
  expect(toExt(fields, { count: 3 })).toEqual({});
});

it("gathers fields across the server's allOf so a referenced required field can be filled", () => {
  const fields = fieldsOf(allOf);
  expect(fields.map((f) => [f.key, f.required, f.private])).toEqual([
    ["a", true, false],
    ["b", false, false],
    ["size", false, true],
  ]);
  // Both bounds apply to size: the stricter one is what the form checks.
  expect(fields.find((f) => f.key === "size")?.schema).toMatchObject({
    type: "integer",
    minimum: 3,
  });
  expect(toExt(fields, { a: 1, b: "x", size: 4 })).toEqual({ a: 1, b: "x" });
});

it("keeps private fields out of the public offer form when they come through allOf", () => {
  expect(Object.keys(publicSchema(allOf).properties ?? {})).toEqual(["a", "b"]);
  expect(publicSchema(allOf).required).toEqual(["a"]);
});
