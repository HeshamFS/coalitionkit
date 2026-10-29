// SPDX-License-Identifier: Apache-2.0
// Entry of the MCP App view (ui://coalitionkit/surface-v1.html). No fonts are bundled: the view
// runs under the host's closed CSP, which allows none, so it uses the system faces.
import "../styles/tokens.css";
import "../styles/base.css";
import "../styles/ext.css";
import "../styles/app.css";
import "../styles/mcpapp.css";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { connectBridge } from "./bridge";
import { McpView } from "./McpView";

const el = document.getElementById("root");
if (el) {
  const { bridge, connected } = connectBridge();
  connected.catch(() => {
    el.textContent = "This view needs an MCP host.";
  });
  createRoot(el).render(
    <StrictMode>
      <McpView bridge={bridge} />
    </StrictMode>,
  );
}
