// SPDX-License-Identifier: Apache-2.0
// The Table fits one screen, and a long list of choices never pushes the page sideways.
import { expect, test } from "@playwright/test";

const SCENES = [
  "arrive",
  "brief",
  "work",
  "compare",
  "plans",
  "commit",
  "make",
  "live",
  "change",
  "ended",
];
const SIZES = [
  { width: 1440, height: 900 },
  { width: 1568, height: 726 },
  { width: 1280, height: 700 },
];

for (const size of SIZES) {
  test(`fits ${size.width}x${size.height} with no page scroll`, async ({ page }) => {
    await page.setViewportSize(size);
    for (const scene of SCENES) {
      await page.goto(`/gallery/table?scene=${scene}&lights=day`);
      await page.waitForSelector(".tb-sheet");
      const m = await page.evaluate(() => ({
        h: document.documentElement.scrollHeight,
        w: document.documentElement.scrollWidth,
        bar: document.querySelector(".tbg-bar")?.getBoundingClientRect().height ?? 0,
      }));
      // The gallery's own strip sits above the room; the room itself must fill what is left.
      expect(m.h, `${scene} height`).toBeLessThanOrEqual(size.height);
      expect(m.w, `${scene} width`).toBeLessThanOrEqual(size.width);
    }
  });
}

test("six selected time slots wrap and never scroll the page sideways", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/gallery/table?scene=brief&lights=day");
  const chips = page.locator(".tb-brief .f01-options button");
  await expect(chips).toHaveCount(6);
  for (let i = 0; i < 6; i++) await chips.nth(i).click();
  const m = await page.evaluate(() => {
    const box = document.querySelector(".tb-brief .f01-options") as HTMLElement;
    return {
      page: document.documentElement.scrollWidth - innerWidth,
      box: box.scrollWidth - box.clientWidth,
      pressed: document.querySelectorAll(".tb-brief .f01-options [aria-pressed=true]").length,
    };
  });
  expect(m.pressed).toBe(6);
  expect(m.box).toBeLessThanOrEqual(0);
  expect(m.page).toBeLessThanOrEqual(0);
  // One click on Send, with no dropdown to close first.
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText(/Your agent asks · 2 of 3/i)).toBeVisible();
});
