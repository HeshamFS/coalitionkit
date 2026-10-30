// SPDX-License-Identifier: Apache-2.0
import { Drawn } from "../../gallery/Drawn";

const tips = [
  ["signed", "Signed", "Signed by the host at 21:52"],
  ["vault", "Vault answer", "Your vault said yes. The number stayed with you."],
  ["estimate", "Estimate", "Estimate from the file app, not a quote"],
];
export function TooltipPanel() {
  return (
    <div className="stage stage-dots" style={{ alignItems: "flex-start", gap: 14, padding: 14 }}>
      {tips.map(([kind, label, tip]) => (
        <Drawn
          key={kind}
          components={[
            {
              id: "root",
              component: "Column",
              spacing: { value: 6, event_ref: "example" },
              children: ["tip", "target"],
            },
            {
              id: "tip",
              component: "Tooltip",
              target: "target",
              tip,
              ...(kind === "estimate" ? { shortcut: "?" } : {}),
            },
            { id: "target", component: "Badge", kind, label },
          ]}
        />
      ))}
    </div>
  );
}
