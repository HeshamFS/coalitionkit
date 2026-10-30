// SPDX-License-Identifier: Apache-2.0
// The renderer draws the whole agreed catalog: every component in spec/catalog is registered, and
// every registered component's props are the catalog's props, no more and none missing.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { z } from "zod";
import { implementations } from ".";

type Spec = { family: string; props: Record<string, { required?: boolean }> };
const file = join(process.cwd(), "..", "..", "spec", "catalog", "coalitionkit-v0_9.json");
const catalog = JSON.parse(readFileSync(file, "utf-8")) as {
  components: Record<string, Spec>;
};
const registered = new Map(implementations.map((i) => [i.name, i]));
const families = [...new Set(Object.values(catalog.components).map((c) => c.family))].sort();

/** Prop names an implementation's schema accepts, minus the A2UI envelope fields. */
function propsOf(name: string): string[] {
  const schema = registered.get(name)?.schema;
  const shape = schema instanceof z.ZodObject ? (schema.shape as Record<string, unknown>) : {};
  return Object.keys(shape)
    .filter((k) => !["id", "component", "accessibility", "weight"].includes(k))
    .sort();
}

describe.each(families)("catalog family %s", (family) => {
  const names = Object.entries(catalog.components)
    .filter(([, c]) => c.family === family)
    .map(([n]) => n);

  it("registers every component", () => {
    expect(names.filter((n) => !registered.has(n))).toEqual([]);
  });

  it.each(names)("%s takes exactly the catalog's props", (name) => {
    if (!registered.has(name)) return;
    expect(propsOf(name)).toEqual(Object.keys(catalog.components[name]?.props ?? {}).sort());
  });
});

it("registers nothing outside the catalog", () => {
  expect([...registered.keys()].filter((n) => !(n in catalog.components))).toEqual([]);
});
