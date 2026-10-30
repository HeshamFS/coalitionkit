// SPDX-License-Identifier: Apache-2.0
import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { examples as e08 } from "../components/f08/examples";
import { examples as e09 } from "../components/f09/examples";
import { examples as e10 } from "../components/f10/examples";
import { examples as e11 } from "../components/f11/examples";
import { Sheet08 } from "./sheets/Sheet08";
import { Sheet09 } from "./sheets/Sheet09";
import { Sheet10 } from "./sheets/Sheet10";
import { Sheet11 } from "./sheets/Sheet11";

afterEach(cleanup);
describe.each([
  ["08", Sheet08, e08],
  ["09", Sheet09, e09],
  ["10", Sheet10, e10],
  ["11", Sheet11, e11],
] as const)("sheet %s", (family, Sheet, examples) => {
  it("renders every example through the catalog without fallback", () => {
    const { container } = render(<Sheet />);
    expect(container.querySelector(`[data-testid="sheet-${family}"]`)).not.toBeNull();
    expect(container.querySelector("[data-fallback]")).toBeNull();
    if (family === "09") {
      expect(container.querySelectorAll("[data-panel]")).toHaveLength(14);
      for (const example of examples) {
        expect(
          container.querySelector(`[data-component="${example.name}"]`),
          example.name,
        ).not.toBeNull();
      }
      return;
    }
    for (const example of examples) {
      const count =
        family === "08" && example.name === "PrivateField"
          ? 3
          : family === "08" && example.name === "ApprovalButton"
            ? example.states.length + 1
            : example.states.length;
      expect(
        container.querySelectorAll(`section[data-component="${example.name}"]`).length,
        example.name,
      ).toBe(count);
    }
  });
});
