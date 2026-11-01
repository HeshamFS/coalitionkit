// SPDX-License-Identifier: Apache-2.0
import { expect, it } from "vitest";
import { fieldsOf, toExt } from "./extSchema";
import offer from "./fixtures/bundled-offer.json";

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
