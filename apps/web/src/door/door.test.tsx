// SPDX-License-Identifier: Apache-2.0
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import readQr from "jsqr";
import { afterEach, describe, expect, it, vi } from "vitest";
import { QrCard } from "./QrCard";
import { PLATE, qrShapes, seatSpots, VIEW } from "./qr";

const LINK = "http://127.0.0.1:8853/join#oOy1E0WkhXbq8hYwqG7wP2rUe3m4nS5tV6xZ9aBcDeF";

/** Paints the same shapes the page draws, at the size of a small phone photo of the code. */
function paint(text: string, scale = 3) {
  const size = VIEW * scale;
  const px = new Uint8ClampedArray(size * size * 4).fill(255);
  const put = (x: number, y: number, [r, g, b]: number[]) => {
    const at = (y * size + x) * 4;
    px[at] = r ?? 0;
    px[at + 1] = g ?? 0;
    px[at + 2] = b ?? 0;
  };
  const disc = (cx: number, cy: number, r: number, colour: number[]) => {
    for (let y = Math.floor((cy - r) * scale); y <= (cy + r) * scale; y++)
      for (let x = Math.floor((cx - r) * scale); x <= (cx + r) * scale; x++)
        if ((x / scale - cx) ** 2 + (y / scale - cy) ** 2 <= r * r) put(x, y, colour);
  };
  const shapes = qrShapes(text);
  const ink = [11, 18, 32];
  for (const m of shapes.marks) {
    if (m.kind === "dot") disc(m.x, m.y, m.r, ink);
    else
      for (let y = Math.floor(m.y * scale); y < (m.y + m.size) * scale; y++)
        for (let x = Math.floor(m.x * scale); x < (m.x + m.size) * scale; x++) put(x, y, ink);
  }
  disc(shapes.goal.x, shapes.goal.y, shapes.goal.clear, [255, 255, 255]);
  disc(shapes.goal.x, shapes.goal.y, shapes.goal.dot, [29, 77, 240]);
  return { px, size };
}

afterEach(cleanup);

describe("the room's QR", () => {
  it("still reads as the invitation with round dots and the goal dot on it", () => {
    const { px, size } = paint(LINK);
    expect(readQr(px, size, size)?.data).toBe(LINK);
  });

  it("stays inside the plate", () => {
    for (const m of qrShapes(LINK).marks) {
      expect(m.x).toBeGreaterThanOrEqual(PLATE.x);
      expect(m.y).toBeLessThanOrEqual(PLATE.y + PLATE.size);
    }
  });

  it("rings the seats without running them together or off the drawing", () => {
    for (const seats of [1, 2, 4, 11, 40]) {
      const spots = seatSpots(seats);
      expect(spots).toHaveLength(seats);
      for (const s of spots) {
        expect(s.x - s.r).toBeGreaterThanOrEqual(0);
        expect(s.y + s.r).toBeLessThanOrEqual(VIEW);
      }
      for (let i = 1; i < seats; i++) {
        const [a, b] = [spots[i - 1], spots[i]];
        if (a && b) expect(Math.hypot(a.x - b.x, a.y - b.y)).toBeGreaterThan(a.r * 2);
      }
    }
  });
});

describe("the QR card", () => {
  it("never writes the secret on the page, shows the seats, and closes with Escape", async () => {
    const onClose = vi.fn();
    render(<QrCard link={LINK} goal="A goal" seats={5} onClose={onClose} />);
    expect(screen.getByRole("dialog", { name: "Scan to take a seat" })).toBeTruthy();
    expect(screen.getByRole("img", { name: /ring of 5 seats, 1 taken/ })).toBeTruthy();
    expect(document.body.innerHTML).not.toContain("oOy1E0Wkh");
    expect(document.activeElement).toBe(screen.getByRole("button", { name: "Done" }));
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalled();
  });

  it("hands focus back when it closes", () => {
    const opener = document.createElement("button");
    document.body.append(opener);
    opener.focus();
    const view = render(<QrCard link={LINK} goal="" seats={2} onClose={() => {}} />);
    expect(document.activeElement).not.toBe(opener);
    view.unmount();
    expect(document.activeElement).toBe(opener);
    opener.remove();
  });

  it("keeps Tab inside and copies the whole link", async () => {
    const writeText = vi.fn(async () => {});
    render(<QrCard link={LINK} goal="" seats={2} onClose={() => {}} />);
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
    await userEvent.tab();
    const copy = screen.getByRole("button", { name: "Copy link" });
    expect(document.activeElement).toBe(copy);
    await userEvent.tab();
    expect(document.activeElement).toBe(screen.getByRole("button", { name: "Done" }));
    await userEvent.click(copy);
    expect(writeText).toHaveBeenCalledWith(LINK);
    expect(await screen.findByRole("button", { name: "Copied" })).toBeTruthy();
  });
});
