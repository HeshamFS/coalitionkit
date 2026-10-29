// SPDX-License-Identifier: Apache-2.0
import { mkdirSync } from "node:fs";
import { expect, test } from "@playwright/test";

const OUT = "test-results/gallery";

for (const theme of ["light", "dark"] as const) {
  test(`gallery screenshot, ${theme}`, async ({ page }) => {
    mkdirSync(OUT, { recursive: true });
    await page.goto(`/gallery?theme=${theme}`);
    await expect(page.getByTestId("gallery")).toBeVisible();
    await page.evaluate(() => document.fonts.ready);
    await expect(page.locator("[data-component]").first()).toBeVisible();
    await page.screenshot({ path: `${OUT}/gallery-${theme}.png`, fullPage: true });
  });
}
