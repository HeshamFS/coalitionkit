// SPDX-License-Identifier: Apache-2.0
import { Drawn } from "../../gallery/Drawn";
import mark from "./mark.svg";

export function McpExample() {
  return (
    <div className="f03-client-frame">
      <div className="f03-client-heading">
        <b>Any chat client</b>
        <span>with the coalitionkit MCP server connected</span>
      </div>
      <div className="f03-client-body">
        <div className="f03-client-message">What's waiting for me in the coalition?</div>
        <div className="f03-client-tool">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.5 2.5-2.8-2.8z" />
          </svg>
          called <span>coalitionkit.my_view</span>
        </div>
        <Drawn
          data={{ mark }}
          components={[
            {
              id: "root",
              component: "McpAppView",
              resourceUri: "ui://coalitionkit/surface-v1.html",
              tree: ["header", "plan", "task"],
            },
            {
              id: "header",
              component: "Row",
              align: "center",
              gap: "8",
              children: ["logo", "title", "stage"],
            },
            { id: "logo", component: "Image", alt: "CoalitionKit", src: { path: "/mark" } },
            { id: "title", component: "Heading", text: "Three-member project", variant: "h3" },
            { id: "stage", component: "Badge", kind: "signed", label: "Decide" },
            { id: "plan", component: "Card", children: ["plan-row"] },
            {
              id: "plan-row",
              component: "Row",
              align: "center",
              children: ["plan-title", "plan-status"],
            },
            {
              id: "plan-title",
              component: "Heading",
              text: "Plan A · send Wednesday",
              variant: "h3",
            },
            { id: "plan-status", component: "Tag", kind: "needs", label: "Needs you" },
            { id: "task", component: "Card", children: ["task-row"] },
            {
              id: "task-row",
              component: "Row",
              align: "center",
              children: ["task-title", "task-status"],
            },
            { id: "task-title", component: "Heading", text: "Task run Thursday", variant: "h3" },
            { id: "task-status", component: "Tag", kind: "agreed", label: "Agreed" },
          ]}
        />
        <span className="f03-client-response">
          One decision waits for you: Plan A. Want me to open it?
        </span>
      </div>
    </div>
  );
}
