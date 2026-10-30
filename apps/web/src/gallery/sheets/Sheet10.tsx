// SPDX-License-Identifier: Apache-2.0
import { PreviewState } from "../../components/f08/shared";
import { examples } from "../../components/f10/examples";
import { Cell, Family, State } from "../Cell";
import { One } from "../Drawn";
import "../../styles/f10.css";

const sections = [
  {
    number: "10a",
    heading: "Mint: from a recording to a live agent",
    cells: [
      { names: ["CaptureCard"], span: null },
      { names: ["MintPipeline"], span: 3 },
      { names: ["AttackTests"], span: null },
      { names: ["PublishApproval"], span: null },
      { names: ["MintedAgentCard"], span: null },
      { names: ["EdgeReaderStatus"], span: null },
    ],
  },
  {
    number: "10b",
    heading: "Devices: readings, alarms and schedule",
    cells: [
      { names: ["DeviceReading"], span: 2 },
      { names: ["DeviceAlarm"], span: null },
      { names: ["ScheduleTwin"], span: null },
    ],
  },
] as const;
const drawnCounts: Record<string, number> = {};
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
export function Sheet10() {
  return (
    <div className="sheet" data-testid="sheet-10">
      <div className="sheet-head">
        <div>
          <div className="eyebrow">coalitionkit/v0_9 · family 10 · example data</div>
          <div className="sheet-title">Mint and devices</div>
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
