// SPDX-License-Identifier: Apache-2.0
import { A2uiSurface } from "@a2ui/react/v0_9";
import { render } from "@testing-library/react";
import { expect, vi } from "vitest";
import { SurfaceBook } from "../../feed/surfaces";
import { examples } from "./examples";

export function draw(
  name: string,
  props?: Record<string, unknown>,
  data?: Record<string, unknown>,
  children: Record<string, unknown>[] = [],
) {
  const dispatch = vi.fn();
  const book = new SurfaceBook(dispatch);
  const example = examples(name)[0];
  book.apply("test", [
    { version: "v0.9", createSurface: { surfaceId: "test", catalogId: "coalitionkit/v0_9" } },
    {
      version: "v0.9",
      updateComponents: {
        surfaceId: "test",
        components: [{ id: "root", component: name, ...(props ?? example?.props) }, ...children],
      },
    },
    {
      version: "v0.9",
      updateDataModel: { surfaceId: "test", path: "/", value: data ?? example?.data ?? {} },
    },
  ]);
  const surface = book.list()[0];
  expect(surface?.fallback).toBe(false);
  const view = render(<A2uiSurface surface={required(surface).model} />);
  return { dispatch, ...view };
}
export function event(
  dispatch: ReturnType<typeof vi.fn>,
  name: string,
  context: Record<string, unknown> = {},
) {
  expect(dispatch).toHaveBeenCalledWith(
    expect.objectContaining({ name, context: expect.objectContaining(context) }),
  );
}
export function required<T>(value: T | null | undefined): T {
  if (value == null) throw new Error("Expected a rendered value");
  return value;
}
