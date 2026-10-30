// SPDX-License-Identifier: Apache-2.0
import { panels } from "../../components/f03/panels";
import { variants } from "../../components/f03/variants";
import { Family } from "../Cell";
import { Drawn } from "../Drawn";

export function Sheet03() {
  return (
    <div className="ck-sheet ck-sheet-03" data-testid="sheet-03">
      <div className="sheet-head">
        <div>
          <div className="eyebrow">coalitionkit/v0_9 · family 03 · example data</div>
          <div className="sheet-title">Conversation and calls</div>
          <div className="sheet-sub">
            Where people and agents talk: private agent chat, the shared thread, live calls with a
            diarized transcript, agents negotiating in the open, and CoalitionKit inside another
            chat app.
          </div>
        </div>
        <div className="h-right">
          <span className="badge b-example">Example data</span>
          <span className="scope">agent session · feed session</span>
        </div>
      </div>
      {panels.map((group, index) => (
        <Family key={group.title} n={`03${String.fromCharCode(97 + index)}`} title={group.title}>
          {group.panels.map((panel) => (
            <div
              key={panel.title}
              className={`cell${panel.span > 1 ? ` span${panel.span}` : ""}`}
              data-panel={panel.title}
            >
              <div className="head">
                <span className="cell-name">{panel.title}</span>
                {panel.name === "AvailabilityGrid" && (
                  <span className="h-right">
                    <span className="badge b-vault">Vault</span>
                    <span className="badge b-measured">PSI-ready</span>
                  </span>
                )}
              </div>
              <div className={`demo ck-demo-${panel.name}`}>
                {variants(panel.name).map((props, i) => (
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
                ))}
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
