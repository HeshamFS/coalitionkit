// SPDX-License-Identifier: Apache-2.0

import { examples } from "../../components/f08/examples";
import { panels } from "../../components/f08/panels";
import {
  DisclosurePreviews,
  PrivacyCharterRevision,
  PrivacyDoor,
  PrivacyFieldLayout,
} from "../../components/f08/presentation";
import { PreviewState } from "../../components/f08/shared";
import { Family } from "../Cell";
import { One } from "../Drawn";
import "../../styles/f08.css";

const sections = [
  {
    number: "08a",
    heading: "The vault and how much leaves it",
    cells: [
      { names: ["VaultCard"], span: null },
      { names: ["DisclosureLadder"], span: 2 },
      { names: ["PrivateField"], span: null },
      { names: ["OverlapView"], span: 2 },
      { names: ["WhatOthersKnow"], span: 2 },
    ],
  },
  {
    number: "08b",
    heading: "Who sees it: scopes, projections and redaction",
    cells: [
      { names: ["ScopeBadge"], span: null },
      { names: ["ProjectionNote"], span: null },
      { names: ["RedactionDiff"], span: null },
      { names: ["CanaryMonitor"], span: null },
    ],
  },
  {
    number: "08c",
    heading: "Consent: deciding, approving, tallying",
    cells: [
      { names: ["ConsentCard"], span: 2 },
      { names: ["VoteTally"], span: null },
      { names: ["StaleNotice"], span: null },
      { names: ["CommitmentCard"], span: null },
      { names: ["ApprovalButton"], span: null },
      { names: ["DurableConsent"], span: 2 },
      { names: ["DecisionLog"], span: 2 },
    ],
  },
] as const;
const drawnCounts: Record<string, number> = {
  ScopeBadge: 7,
  VoteTally: 2,
  CommitmentCard: 4,
  ApprovalButton: 2,
};
function Samples({ name }: { name: string }) {
  const example = examples.find((e) => e.name === name);
  if (!example) return null;
  if (name === "PrivateField") return <PrivateFields />;
  const count = drawnCounts[name] ?? 1;
  const states =
    name === "OverlapView"
      ? [...example.states].sort((a) => (a.state === "done" ? -1 : 1))
      : example.states;
  return (
    <>
      {states.slice(0, count).map((s) => (
        <PreviewState key={s.state} value={s.state}>
          <One component={name} props={s.props} />
        </PreviewState>
      ))}
      {name === "ApprovalButton" && (
        <PrivacyDoor value="lens">
          <One component={name} props={{ ...states[0]?.props, label: "Approve item?" }} />
        </PrivacyDoor>
      )}
      <div hidden>
        {states.slice(count).map((s) => (
          <PreviewState key={s.state} value={s.state}>
            <One component={name} props={s.props} />
          </PreviewState>
        ))}
      </div>
    </>
  );
}
function PrivateFields() {
  return (
    <>
      <PrivacyFieldLayout value={{ label: "Usage limit", unit: "per cycle" }}>
        <One
          component="PrivateField"
          props={{
            display: "••••",
            policy: "vault",
            reveal: { value: 10, event_ref: "example:1" },
          }}
        />
      </PrivacyFieldLayout>
      <PrivacyFieldLayout value={{ label: "Phone" }}>
        <One
          component="PrivateField"
          props={{ display: "+351 •••• ••• 21", policy: "never shared" }}
        />
      </PrivacyFieldLayout>
      <PrivacyFieldLayout value={{ label: "Start" }}>
        <One component="PrivateField" props={{ display: "09:05", policy: "shared with task" }} />
      </PrivacyFieldLayout>
    </>
  );
}
export function Sheet08() {
  return (
    <DisclosurePreviews
      value={{
        "Usage limit": { question: '"Is €96 within your limit?"', answer: "yes", exact: '"€140"' },
      }}
    >
      <PrivacyCharterRevision value="3">
        <div className="sheet f08-sheet" data-testid="sheet-08">
          <div className="sheet-head">
            <div>
              <div className="eyebrow">coalitionkit/v0_9 · family 08 · example data</div>
              <div className="sheet-title">Privacy and consent</div>
              <div className="sheet-sub">
                What stays yours, what others can learn and how little, who sees each thing, and
                every moment where nothing happens until a person says yes with their own key.
              </div>
            </div>
            <div className="h-right">
              <span className="badge b-example">Example data</span>
              <span className="scope">vault · scope · PSI · consent</span>
            </div>
          </div>
          {sections.map((section) => (
            <Family key={section.number} n={section.number} title={section.heading}>
              {section.cells.map((cell) => {
                const name = cell.names[0];
                const panel = panels[name];
                if (!panel) return null;
                return (
                  <div key={name} className={`cell${cell.span ? " span2" : ""}`} data-panel={name}>
                    <div className="head">
                      <span className="cell-name">
                        {name} · {panel.title}
                      </span>
                      {panel.badge && (
                        <span className={`h-right badge b-${panel.tone}`}>{panel.badge}</span>
                      )}
                      {panel.doors && (
                        <span className="h-right door">
                          {panel.doors.map((d) => (
                            <span key={d}>{d}</span>
                          ))}
                        </span>
                      )}
                    </div>
                    <div className="demo">
                      <Samples name={name} />
                    </div>
                    <div className="props">{panel.props}</div>
                  </div>
                );
              })}
            </Family>
          ))}
        </div>
      </PrivacyCharterRevision>
    </DisclosurePreviews>
  );
}
