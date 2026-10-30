// SPDX-License-Identifier: Apache-2.0
// Builds the MCP App view as ONE html file with script and style inlined and no external request.
// It is written into the MCP server package, which serves it as ui://coalitionkit/surface-v1.html.
import { resolve } from "node:path";
import react from "@vitejs/plugin-react";
import postcss from "postcss";
import { defineConfig } from "vite";
import { viteSingleFile } from "vite-plugin-singlefile";

export default defineConfig({
  mode: "production",
  resolve: {
    // Let Vite share and tree-shake SDK dependencies instead of embedding the
    // SDK's prebundled copy alongside the catalog's dependencies.
    alias: [
      {
        find: "@modelcontextprotocol/ext-apps/app-with-deps",
        replacement: "@modelcontextprotocol/ext-apps",
      },
    ],
  },
  plugins: [
    react(),
    {
      name: "mcp-compact-styles",
      enforce: "post",
      generateBundle(_, bundle) {
        for (const asset of Object.values(bundle)) {
          if (asset.type !== "asset" || !asset.fileName.endsWith(".css")) continue;
          const root = postcss.parse(String(asset.source));
          // The host CSP disallows fonts. Use the existing system fallbacks.
          root.walkAtRules("font-face", (rule) => {
            rule.remove();
          });
          // Keep the last identical rule so the cascade stays unchanged.
          const seen = new Set<string>();
          for (const node of [...root.nodes].reverse()) {
            const key = node.toString();
            if (seen.has(key)) node.remove();
            else seen.add(key);
          }
          asset.source = root.toString();
        }
      },
    },
    viteSingleFile({ removeViteModuleLoader: true }),
  ],
  build: {
    outDir: resolve(import.meta.dirname, "../../packages/mcp_server/src/coalitionkit_mcp/assets"),
    emptyOutDir: false,
    target: "es2023",
    minify: "oxc",
    cssMinify: true,
    assetsInlineLimit: Number.MAX_SAFE_INTEGER,
    cssCodeSplit: false,
    modulePreload: false,
    rollupOptions: { input: resolve(import.meta.dirname, "surface-v1.html") },
  },
});
