// SPDX-License-Identifier: Apache-2.0
import { Children, Frame, text, type View } from "../f02/ui";
import "./mcp.css";

export function McpAppView({ p, build }: View) {
  return (
    <Frame name="McpAppView" state={p.tree ? "ready" : "loading"}>
      {p.tree ? <Children value={p.tree} build={build} /> : <p role="status">Loading your view…</p>}
      <span className="f03-mcp-resource">{text(p.resourceUri)} · your projection only</span>
    </Frame>
  );
}
