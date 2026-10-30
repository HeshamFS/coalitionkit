// SPDX-License-Identifier: Apache-2.0
import { PreviewState } from "../../components/f08/shared";
import { examples } from "../../components/f09/examples";
import { Cell, Family, State } from "../Cell";
import { One } from "../Drawn";
import "../../styles/f09.css";

const sections = [
  {
    number: "09a",
    heading: "Live: ripple, activity and presence",
    cells: [
      { names: ["RippleBanner", "ChangedValue"], span: 2 },
      { names: ["ActivityStream"], span: null },
      { names: ["GardenerThinking"], span: null },
      { names: ["CanvasPresence"], span: 2 },
      { names: ["ConnectionStatus", "LiveDocks"], span: null },
      { names: ["StepProgress"], span: null },
    ],
  },
  {
    number: "09b",
    heading: "Proof: the log, the chain, the receipts",
    cells: [
      { names: ["LogStream", "EventRow"], span: 2 },
      { names: ["ChainView"], span: 2 },
      { names: ["ReceiptBadge", "ProvenanceTag"], span: null },
      { names: ["StewardVerdict"], span: null },
      { names: ["EvidenceCard"], span: null },
      { names: ["MediaWithMasks"], span: null },
      { names: ["VerifyPanel"], span: 2 },
      { names: ["ErrorNotice"], span: 2 },
    ],
  },
] as const;
const drawnCounts: Record<string, number> = {
  ChangedValue: 3,
  ConnectionStatus: 3,
  ReceiptBadge: 3,
  ProvenanceTag: 5,
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
export function Sheet09() {
  return (
    <div className="sheet" data-testid="sheet-09">
      <div className="sheet-head">
        <div>
          <div className="eyebrow">coalitionkit/v0_9 · family 09 · example data</div>
          <div className="sheet-title">Live and proof</div>
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
