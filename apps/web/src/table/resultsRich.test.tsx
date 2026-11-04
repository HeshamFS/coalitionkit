// SPDX-License-Identifier: Apache-2.0
// Richer results: a budget's split in its own unit, a timeline in local time, and a picture the
// host keeps for the room, fetched with the viewer's token.
import { A2uiSurface } from "@a2ui/react/v0_9";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { clearToken, saveToken } from "../feed/config";
import { SurfaceBook } from "../feed/surfaces";
import { promptOf } from "./ResultDialog";
import type { RoomResult } from "./room";
import { localTimes } from "./slots";

afterEach(() => {
  cleanup();
  clearToken();
  vi.unstubAllGlobals();
});

function draw(components: Record<string, unknown>[], value: Record<string, unknown> = {}) {
  const book = new SurfaceBook(() => {});
  book.apply("r", [
    { version: "v0.9", createSurface: { surfaceId: "r", catalogId: "coalitionkit/v0_9" } },
    { version: "v0.9", updateComponents: { surfaceId: "r", components } },
    { version: "v0.9", updateDataModel: { surfaceId: "r", path: "/", value } },
  ]);
  const entry = book.list()[0];
  if (!entry || entry.fallback) throw new Error("Catalog fallback");
  return render(<A2uiSurface surface={entry.model} />);
}

it("shows a budget's lines and total in the unit the host wrote", () => {
  draw([
    {
      id: "root",
      component: "CostSplit",
      items: [
        { label: "Hall", payer: "all", amount: "200 USD", kind: "estimate" },
        { label: "Food", payer: "shared", amount: "100 USD", kind: "estimate" },
      ],
    },
  ]);
  expect(screen.getByText("200 USD")).toBeTruthy();
  expect(screen.getByText("300 USD")).toBeTruthy();
});

it("turns a timeline's ISO times into the viewer's local time", () => {
  const [, parts] = localTimes([
    {},
    {
      updateComponents: {
        components: [
          {
            id: "t",
            component: "Timeline",
            items: [{ start: "2031-06-05T16:00:00Z", title: "x" }],
          },
        ],
      },
    },
  ]) as { updateComponents: { components: { items: { start: string }[] }[] } }[];
  const start = parts?.updateComponents.components[0]?.items[0]?.start ?? "";
  expect(start).not.toContain("T16:00");
  expect(start).toMatch(/\d{2}[:.]\d{2}/);
});

it("fetches a room picture with the viewer token and draws it from a local address", async () => {
  saveToken("viewer-token");
  const fetched = vi.fn(async () => ({ ok: true, blob: async () => new Blob(["png"]) }));
  vi.stubGlobal("fetch", fetched);
  const urls = URL as unknown as Record<string, unknown>;
  urls.createObjectURL = vi.fn(() => "blob:picture");
  urls.revokeObjectURL = vi.fn();
  const hash = "a".repeat(64);
  draw([{ id: "root", component: "Image", alt: "A poster", src: { path: "/image/src" } }], {
    image: { src: `/v1/room/media/${hash}` },
  });
  await waitFor(() =>
    expect(screen.getByAltText("A poster").getAttribute("src")).toBe("blob:picture"),
  );
  const [url, init] = fetched.mock.calls[0] as unknown as [string, RequestInit];
  expect(url.endsWith(`/v1/room/media/${hash}`)).toBe(true);
  expect((init.headers as Record<string, string>).Authorization).toBe("Bearer viewer-token");
});

it("never sends the token for a picture from anywhere else", () => {
  saveToken("viewer-token");
  const fetched = vi.fn();
  vi.stubGlobal("fetch", fetched);
  draw([{ id: "root", component: "Image", alt: "Other", src: { path: "/src" } }], {
    src: "https://example.org/x.png",
  });
  expect(screen.getByAltText("Other").getAttribute("src")).toBe("https://example.org/x.png");
  expect(fetched).not.toHaveBeenCalled();
});

it("shows the prompt of a picture under the work, and nothing for other kinds", () => {
  const base = { kind: "image", data: { prompt: "A poster for a small group" } } as RoomResult;
  expect(promptOf(base)).toBe("A poster for a small group");
  expect(promptOf({ ...base, kind: "draft" })).toBe("");
});
