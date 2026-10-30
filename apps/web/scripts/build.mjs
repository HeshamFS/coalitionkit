// SPDX-License-Identifier: Apache-2.0
// Builds the app and, from the second entry, the single-file MCP App view. Run with
// `--mcp-only` to build just the view (it is written into packages/mcp_server).
import { build } from "vite";

const mcpOnly = process.argv.includes("--mcp-only");
if (!mcpOnly) await build();
await build({ configFile: "vite.config.mcp.ts" });
