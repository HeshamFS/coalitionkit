// SPDX-License-Identifier: Apache-2.0
import { apis } from "../../catalog/families/f01";
import { PanelDemo, Sample } from "../../components/f01/PanelDemo";
import { panels } from "../../components/f01/panels";
import { Family } from "../Cell";
import { One } from "../Drawn";

export { examples } from "../../components/f01/examples";

const sections: [string, string, number, number][] = [
  ["01a", "Buttons and actions", 0, 4],
  ["01b", "Text and numbers", 4, 8],
  ["01c", "Choice", 8, 15],
  ["01d", "Date and time", 15, 18],
  ["01e", "Overlays: tooltip, popover, menu, modal, sheet, drawer", 18, 26],
  ["01f", "Progress, loading, empty and error", 26, 30],
  ["01g", "Command palette and data display", 30, 36],
  ["01h", "Media and files", 36, 40],
];
const layout = ["Text", "Heading", "RichText", "Icon", "Row", "Column", "Grid", "Card", "Panel"];

export function Sheet01() {
  return (
    <div className="sheet sheet-01" data-testid="sheet-01">
      <div className="sheet-head">
        <div>
          <div className="eyebrow">coalitionkit/v0_9 · family 01 · example data</div>
          <div className="sheet-title">Foundations: controls, overlays and states</div>
          <div className="sheet-sub">
            The parts every generated screen is built from. Each cell shows the component working,
            in every state an agent can ask for.
          </div>
        </div>
        <div className="h-right">
          <One component="Badge" props={{ kind: "example", label: "Example data" }} />
          <span className="scope">wide · compact · lens · message · voice</span>
        </div>
      </div>
      {sections.map(([n, title, start, end]) => (
        <Family key={n} n={n} title={title}>
          {panels.slice(start, end).map((panel, index) => (
            <div className={`cell${panel.span === 2 ? " span2" : ""}`} key={panel["cell-name"]}>
              <div className="head">
                <span className="cell-name">{panel["cell-name"]}</span>
                <PanelDoor index={start + index} />
              </div>
              <div className="demo">
                <PanelDemo index={start + index} />
              </div>
              <div className="props">{panel.props}</div>
              {panel.evts && <div className="evts">{panel.evts}</div>}
            </div>
          ))}
        </Family>
      ))}
      <Family n="01i" title="Typography and layout · additional catalog primitives">
        {layout.map((name) => (
          <div className="cell" key={name}>
            <div className="head">
              <span className="cell-name">{name}</span>
            </div>
            <div className="demo">
              <Sample name={name} />
            </div>
            <div className="props">
              {Object.keys(apis.find((a) => a.name === name)?.schema.shape ?? {}).join(" · ")}
            </div>
          </div>
        ))}
      </Family>
    </div>
  );
}

function PanelDoor({ index }: { index: number }) {
  if (index === 16)
    return (
      <span className="h-right">
        <One component="Badge" props={{ kind: "measured", label: "Measured" }} />
        <One component="Badge" props={{ kind: "vault", label: "PSI" }} />
      </span>
    );
  if (![0, 22, 23, 30].includes(index)) return null;
  return (
    <span className="h-right door">
      <span>{index === 22 ? "compact" : "wide"}</span>
      {index === 0 && <span>compact</span>}
    </span>
  );
}
