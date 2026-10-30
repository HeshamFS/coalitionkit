// SPDX-License-Identifier: Apache-2.0
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { One } from "../../gallery/Drawn";

afterEach(cleanup);

it("labels a masked field and its unit through catalog props without a surface provider", () => {
  const { container } = render(
    <One
      component="PrivateField"
      props={{ label: "Usage limit", unit: "per cycle", display: "••••", policy: "vault" }}
    />,
  );
  expect(container.querySelector("[data-fallback]")).toBeNull();
  expect(screen.getByRole("group", { name: "Usage limit vault" })).toBeTruthy();
  expect(screen.getByText("per cycle")).toBeTruthy();
});

it("renders the bound charter revision for a suspended commitment through the catalog", () => {
  const { container } = render(
    <One
      component="CommitmentCard"
      props={{
        subject: { kind: "commitment", id: "c1", revision: { value: 1, event_ref: "e1" } },
        status: "suspended",
        charterRevision: { value: 7, event_ref: "e7" },
      }}
    />,
  );
  expect(container.querySelector("[data-fallback]")).toBeNull();
  expect(screen.getByText("suspended until you accept charter r7")).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Approve" })).toBeNull();
});
