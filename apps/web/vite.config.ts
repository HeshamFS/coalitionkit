// SPDX-License-Identifier: Apache-2.0
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Tests point same-origin /v1 and /mcp at a host. Unset in normal use. The MCP endpoint
    // checks the Host header and refuses a browser Origin it was not told about, so the proxy
    // presents itself as the host and drops the Origin of the test page.
    proxy: process.env.CK_PROXY_TARGET
      ? {
          "/v1": process.env.CK_PROXY_TARGET,
          "/mcp": {
            target: process.env.CK_PROXY_TARGET,
            changeOrigin: true,
            configure: (proxy) => {
              proxy.on("proxyReq", (request) => request.removeHeader("origin"));
            },
          },
        }
      : undefined,
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
