// SPDX-License-Identifier: Apache-2.0
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Media } from "./Media";

afterEach(cleanup);

it("Image retries when its host replaces a failed source", () => {
  const send = vi.fn();
  const build = () => null;
  const { container, rerender } = render(
    <Media name="Image" p={{ src: "/missing.png", alt: "Preview" }} send={send} build={build} />,
  );
  fireEvent.error(screen.getByRole("img"));
  expect(container.querySelector("figure")).toHaveAttribute("data-state", "failed");
  rerender(
    <Media
      name="Image"
      p={{ src: "/replacement.png", alt: "Preview" }}
      send={send}
      build={build}
    />,
  );
  expect(screen.getByRole("img")).toHaveAttribute("src", "/replacement.png");
  fireEvent.load(screen.getByRole("img"));
  expect(container.querySelector("figure")).toHaveAttribute("data-state", "loaded");
});
