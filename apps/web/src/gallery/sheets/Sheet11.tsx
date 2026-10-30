// SPDX-License-Identifier: Apache-2.0
import { PreviewState } from "../../components/f08/shared";
import { examples } from "../../components/f11/examples";
import { Cell, Family, State } from "../Cell";
import { One } from "../Drawn";
import "../../styles/f11.css";

const sections = [
  {
    number: "11a",
    heading: "One component, every door",
    cells: [
      { names: ["DoorMatrix"], span: 4 },
      { names: ["NotificationCard"], span: null },
      { names: ["ChannelSettings"], span: null },
      { names: ["ChannelHandoff"], span: null },
      { names: ["MessageTemplate"], span: null },
    ],
  },
  {
    number: "11b",
    heading: "Ending: dissolve, results and cost",
    cells: [
      { names: ["DissolveSummary"], span: 2 },
      { names: ["CostMeter"], span: null },
      { names: ["Scorecard", "MetricTile"], span: null },
    ],
  },
  {
    number: "11c",
    heading: "What you keep: export, lessons and skills",
    cells: [
      { names: ["ExportControl"], span: null },
      { names: ["LessonReview"], span: 2 },
      { names: ["SkillCard"], span: null },
      { names: ["CoalitionArchive"], span: 2 },
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
export function Sheet11() {
  return (
    <div className="sheet" data-testid="sheet-11">
      <div className="sheet-head">
        <div>
          <div className="eyebrow">coalitionkit/v0_9 · family 11 · example data</div>
          <div className="sheet-title">Doors, memory and ending</div>
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
