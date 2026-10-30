// SPDX-License-Identifier: Apache-2.0
// The doors test: a real coalitionkit-server (started by the test), the room, the lens and the
// MCP App view inside a test host, all through one dev server that proxies /v1 and /mcp to it.
import { defineConfig } from "@playwright/test";

export const RIG_PORT = 4611;
export const WEB_PORT = 5174;

export default defineConfig({
  testDir: "./e2e/doors",
  outputDir: "./test-results/pw-doors",
  fullyParallel: false,
  workers: 1,
  timeout: 240_000,
  reporter: [["list"]],
  use: {
    baseURL: `http://127.0.0.1:${WEB_PORT}`,
    viewport: { width: 1440, height: 900 },
  },
  webServer: {
    command: `npx vite --host 0.0.0.0 --port ${WEB_PORT} --strictPort`,
    url: `http://127.0.0.1:${WEB_PORT}`,
    reuseExistingServer: false,
    env: { CK_PROXY_TARGET: `http://127.0.0.1:${RIG_PORT}` },
    timeout: 60_000,
  },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
});
