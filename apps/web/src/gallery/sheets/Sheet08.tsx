// SPDX-License-Identifier: Apache-2.0

import { examples } from "../../components/f08/examples";
import { PreviewState } from "../../components/f08/shared";
import { Cell, Family, State } from "../Cell";
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
  ApprovalButton: 3,
};
function Samples({ name }: { name: string }) {
  const example = examples.find((e) => e.name === name);
  if (!example) return null;
  const count = drawnCounts[name] ?? 1;
  const draw = (s: (typeof example.states)[number]) => (
    <State key={s.state} label={s.state}>
      <PreviewState value={s.state}>
        <One component={name} props={s.props} />
      </PreviewState>
    </State>
  );
  return (
    <>
      {example.states.slice(0, count).map(draw)}
      {example.states.length > count && (
        <details className="family-extra">
          <summary>Other states</summary>
          {example.states.slice(count).map(draw)}
        </details>
      )}
    </>
  );
}
export function Sheet08() {
  return (
    <div className="sheet" data-testid="sheet-08">
      <div className="sheet-head">
        <div>
          <div className="eyebrow">coalitionkit/v0_9 · family 08 · example data</div>
          <div className="sheet-title">Privacy and consent</div>
        </div>
      </div>
      {sections.map((section) => (
        <Family key={section.number} n={section.number} title={section.heading}>
          {section.cells.map((cell) => {
            const selected = cell.names.map((name) => examples.find((e) => e.name === name));
            return (
              <Cell
                key={cell.names.join(" · ")}
                name={cell.names.join(" · ")}
                span={cell.span ?? undefined}
                props={selected.map((e) => e?.props).join(" · ")}
                events={selected.map((e) => e?.events).join(" · ")}
              >
                {cell.names.map((name) => (
                  <Samples key={name} name={name} />
                ))}
              </Cell>
            );
          })}
        </Family>
      ))}
    </div>
  );
}
