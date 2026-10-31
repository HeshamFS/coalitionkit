// @vitest-environment node
// SPDX-License-Identifier: Apache-2.0
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { canonicalize, canonicalizeText } from "./jcs";

type Case = {
  name: string;
  input_json: string;
  canonical_utf8: string;
  canonical_hex: string;
  sha256: string;
};
type ErrorCase = { name: string; input_json: string };

const file = fileURLToPath(new URL("../../../../spec/vectors/jcs.json", import.meta.url));
const vectors = JSON.parse(readFileSync(file, "utf8")) as {
  cases: Case[];
  error_cases: ErrorCase[];
};

const hex = (bytes: Uint8Array) =>
  Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");

describe("JCS vectors", () => {
  it("has the cases the spec ships", () => {
    expect(vectors.cases.length).toBe(38);
    expect(vectors.error_cases.length).toBe(3);
  });

  for (const c of vectors.cases) {
    it(`canonicalises: ${c.name}`, async () => {
      const text = canonicalizeText(c.input_json);
      expect(text).toBe(c.canonical_utf8);
      const bytes = new TextEncoder().encode(text);
      expect(hex(bytes)).toBe(c.canonical_hex);
      const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes);
      expect(hex(new Uint8Array(digest))).toBe(c.sha256);
    });
  }

  for (const c of vectors.error_cases) {
    it(`refuses: ${c.name}`, () => {
      expect(() => canonicalizeText(c.input_json)).toThrow();
    });
  }

  it("refuses values JSON cannot hold", () => {
    expect(() => canonicalize(Number.NaN)).toThrow();
    expect(() => canonicalize({ a: undefined })).toThrow();
    expect(() => canonicalize("\ud800")).toThrow();
  });
});
