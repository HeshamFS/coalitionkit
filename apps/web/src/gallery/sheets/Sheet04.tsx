// SPDX-License-Identifier: Apache-2.0
import "./Sheet04.css";

import { examples } from "../../components/f04/examples";
import { panels } from "../../components/f04/panels";
import { ValidationExample } from "../../components/f04/validation-example";
import { Family } from "../Cell";
import { Drawn } from "../Drawn";

export function Sheet04() {
  return (
    <div className="ck-sheet ck-sheet-04" data-testid="sheet-04">
      <div className="sheet-head">
        <div>
          <div className="eyebrow">coalitionkit/v0_9 · family 04 · example data</div>
          <div className="sheet-title">Forms and flows</div>
          <div className="sheet-sub">
            How people put things in: forms agents generate from a schema, step-by-step flows, the
            charter, needs and offers, private availability, and the acceptance moments that end in
            a signature.
          </div>
        </div>
        <div className="h-right">
          <span className="badge b-example">Example data</span>
          <span className="scope">submit_event → typed message</span>
        </div>
      </div>
      {panels.map((group, index) => (
        <Family key={group.title} n={`04${String.fromCharCode(97 + index)}`} title={group.title}>
          {group.panels.map((panel) => (
            <div
              key={panel.title}
              className={`cell${panel.span > 1 ? ` span${panel.span}` : ""}`}
              data-panel={panel.title}
            >
              <div className="head">
                <span className="cell-name">{panel.title}</span>
                {panel.name === "Form" && (
                  <span className="h-right door">
                    {(panel.span === 2 ? ["wide", "compact", "voice"] : ["voice"]).map((door) => (
                      <span key={door}>{door}</span>
                    ))}
                  </span>
                )}
                {panel.name === "ConsentSeal" && (
                  <span className="h-right door">
                    <span>compact</span>
                    <span>wide</span>
                  </span>
                )}
                {panel.name === "Wizard" && (
                  <span className="h-right door">
                    <span>wide</span>
                  </span>
                )}
                {panel.name === "AvailabilityGrid" && (
                  <span className="h-right">
                    <span className="badge b-vault">Vault</span>
                    <span className="badge b-measured">PSI-ready</span>
                  </span>
                )}
              </div>
              <div className={`demo ck-demo-${panel.name}`}>
                {panel.name === "ValidationSummary" ? (
                  <ValidationExample />
                ) : (
                  [
                    panel.title === "Form · voice door"
                      ? {
                          title: "Your part of the task",
                          presentation: "voice",
                          conversation: [
                            { role: "agent", text: '"When do you need to finish the task?"' },
                            { role: "user", text: '"By ten tomorrow morning"' },
                            {
                              role: "agent",
                              text: '"Ten tomorrow. What’s the most for a resource? Only your vault keeps it."',
                            },
                            { role: "user", text: '"A hundred forty"' },
                          ],
                          fields: [
                            { id: "finish_by", readback: "2026-10-29T10:00 ✓" },
                            { id: "max_cost", private: "answer-only" },
                            { id: "items" },
                          ],
                        }
                      : (examples[panel.name] ?? {}),
                  ].map((props, i) => (
                    <Drawn
                      key={String(props.state ?? i)}
                      components={[
                        { id: "root", component: panel.name, ...props },
                        {
                          id: "content",
                          component: "Message",
                          text: "Plan A is ready for review.",
                          state: "delivered",
                        },
                      ]}
                    />
                  ))
                )}
              </div>
              <div className="props">{panel.props}</div>
              {panel.events && <div className="evts">{panel.events}</div>}
            </div>
          ))}
        </Family>
      ))}
    </div>
  );
}
