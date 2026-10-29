// SPDX-License-Identifier: Apache-2.0
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Tests point same-origin /v1 at a mock host. Unset in normal use.
    proxy: process.env.CK_PROXY_TARGET ? { "/v1": process.env.CK_PROXY_TARGET } : undefined,
  },
  preview: { port: 4173 },
  test: {
    environment: "jsdom",
    pool: "threads",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    css: false,
  },
});
