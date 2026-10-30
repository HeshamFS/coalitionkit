// SPDX-License-Identifier: Apache-2.0
// A minimal MCP host for the tests: it connects to the real MCP endpoint with a bearer token,
// reads the view named by `my_view`'s UI metadata, puts it in a sandboxed iframe (scripts only,
// no same-origin) and bridges the view with the ext-apps AppBridge. It is not part of the product.

import { Client, StreamableHTTPClientTransport } from "@modelcontextprotocol/client";
import {
  AppBridge,
  getToolUiResourceUri,
  PostMessageTransport,
} from "@modelcontextprotocol/ext-apps/app-bridge";

type Setup = { token: string; coalition: string };
type Logged = { name: string; args: unknown; result: unknown };

declare global {
  interface Window {
    __HOST?: Setup;
    __hostLog: Logged[];
    __hostReady: Promise<string>;
  }
}

async function start(): Promise<string> {
  const setup = window.__HOST;
  if (!setup) throw new Error("no host setup");
  const client = new Client({ name: "test-host", version: "1.0.0" }, { capabilities: {} });
  const transport = new StreamableHTTPClientTransport(new URL("/mcp", location.origin), {
    requestInit: { headers: { Authorization: `Bearer ${setup.token}` } },
  });
  await client.connect(transport);

  const tools = await client.listTools();
  const tool = tools.tools.find((t) => t.name === "my_view");
  const uri = tool ? getToolUiResourceUri(tool) : undefined;
  if (!uri) throw new Error("my_view names no view");
  const resource = await client.readResource({ uri });
  const html = (resource.contents[0] as { text?: string }).text ?? "";

  const iframe = document.getElementById("view") as HTMLIFrameElement;
  const bridge = new AppBridge(
    null,
    { name: "test-host", version: "1.0.0" },
    { serverTools: {}, logging: {} },
  );
  // Forward the view's tool calls to the server, and keep what came back for the tests.
  bridge.oncalltool = async (params) => {
    const result = await client.callTool(params);
    window.__hostLog.push({ name: params.name, args: params.arguments, result });
    return result;
  };
  const args = { coalition_id: setup.coalition, device: "mcp-app" };
  bridge.oninitialized = async () => {
    await bridge.sendToolInput({ arguments: args });
    const result = await client.callTool({ name: "my_view", arguments: args });
    await bridge.sendToolResult(result as never);
  };
  // Listen before the view loads, so its first message is not lost.
  const win = iframe.contentWindow;
  if (!win) throw new Error("no frame");
  await bridge.connect(new PostMessageTransport(win, win));
  iframe.srcdoc = html;
  return uri;
}

window.__hostLog = [];
window.__hostReady = start();
