// SPDX-License-Identifier: Apache-2.0
// The only door out of the view: the MCP Apps bridge. The view makes no network request of its
// own; it reads tool results the host passes in and calls tools through the host.
import { App } from "@modelcontextprotocol/ext-apps/app-with-deps";

export type ToolResult = {
  isError?: boolean;
  structuredContent?: unknown;
  content?: { type: string; text?: string }[];
};

export interface Bridge {
  /** Called with the latest tool result as soon as a listener is set, then with every new one. */
  onToolResult(listener: (result: ToolResult) => void): void;
  callTool(name: string, args: Record<string, unknown>): Promise<ToolResult>;
  onTheme(listener: (theme: "light" | "dark") => void): void;
}

/** The text a result carries for a person: its first text block. */
export function resultText(result: ToolResult): string {
  return result.content?.find((c) => c.type === "text")?.text?.split("\n")[0] ?? "";
}

/** Connects to the host. Handlers are set before `connect`, as the SDK requires. */
export function connectBridge(): { bridge: Bridge; connected: Promise<void> } {
  const app = new App({ name: "coalitionkit-surface", version: "1.0.0" }, {}, { autoResize: true });
  let last: ToolResult | null = null;
  let listener: ((r: ToolResult) => void) | null = null;
  let theme: "light" | "dark" | null = null;
  let themeListener: ((t: "light" | "dark") => void) | null = null;

  app.ontoolresult = (params) => {
    last = params as ToolResult;
    listener?.(last);
  };
  app.onhostcontextchanged = (ctx) => {
    if (ctx.theme === "light" || ctx.theme === "dark") {
      theme = ctx.theme;
      themeListener?.(theme);
    }
  };

  const bridge: Bridge = {
    onToolResult(l) {
      listener = l;
      if (last) l(last);
    },
    onTheme(l) {
      themeListener = l;
      const initial = app.getHostContext()?.theme ?? theme;
      if (initial === "light" || initial === "dark") l(initial);
    },
    callTool: async (name, args) =>
      (await app.callServerTool({ name, arguments: args })) as ToolResult,
  };
  return { bridge, connected: app.connect() };
}
