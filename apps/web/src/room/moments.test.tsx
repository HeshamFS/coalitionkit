// SPDX-License-Identifier: Apache-2.0
import { describe, expect, it } from "vitest";
import { vaultResult } from "./moments";

describe("vault result from the member's own agent channel", () => {
  it("reads the latest vault result line", () => {
    const lines = [
      { text: "hello" },
      { text: JSON.stringify({ vault_result: { match_id: "m1", overlap: ["slot a"], count: 1 } }) },
    ];
    expect(vaultResult(lines)).toEqual({ shared: "slot a" });
  });
  it("shows only a count when the vault reports a count", () => {
    const lines = [{ text: JSON.stringify({ vault_result: { match_id: "m1", count: 2 } }) }];
    expect(vaultResult(lines)).toEqual({ shared: "2 in common" });
  });
  it("finds nothing in ordinary lines", () => {
    expect(vaultResult([{ text: "{not json" }, { text: '{"other":1}' }])).toBeUndefined();
  });
});
