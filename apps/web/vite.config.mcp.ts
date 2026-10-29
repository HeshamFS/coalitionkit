// SPDX-License-Identifier: Apache-2.0
// Builds the MCP App view as ONE html file with script and style inlined and no external request.
// It is written into the MCP server package, which serves it as ui://coalitionkit/surface-v1.html.
import { resolve } from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { viteSingleFile } from "vite-plugin-singlefile";

export default defineConfig({
  plugins: [react(), viteSingleFile({ removeViteModuleLoader: true })],
  build: {
    outDir: resolve(import.meta.dirname, "../../packages/mcp_server/src/coalitionkit_mcp/assets"),
    emptyOutDir: false,
    target: "es2023",
    assetsInlineLimit: Number.MAX_SAFE_INTEGER,
    cssCodeSplit: false,
    modulePreload: false,
    rollupOptions: { input: resolve(import.meta.dirname, "surface-v1.html") },
  },
});
