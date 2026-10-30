// SPDX-License-Identifier: Apache-2.0
import { examples, groups, labels } from "../../components/f02/examples";
import { Cell, Family, State } from "../Cell";
import { Drawn } from "../Drawn";

export function Sheet02() {
  return (
    <div className="ck-sheet" data-testid="sheet-02">
      <div className="sheet-head">
        <div>
          <div className="eyebrow">coalitionkit/v0_9 · family 02 · example data</div>
          <h1 className="sheet-title">Shell, doors and templates</h1>
        </div>
      </div>
      {groups.map(([heading, names], index) => (
        <Family
          key={String(heading)}
          n={`02${String.fromCharCode(97 + index)}`}
          title={String(heading)}
        >
          {(names as string[]).map((name) => (
            <Cell
              key={name}
              name={name}
              props={labels[name]?.props ?? ""}
              events={labels[name]?.events}
              span={
                name === "RoomShell"
                  ? 4
                  : ["EntryComposer", "WiringDrawer", "BoardTemplate"].includes(name)
                    ? 2
                    : undefined
              }
            >
              <div className="ck-examples">
                {variants(name).map((props, i) => (
                  <State key={String(props.state ?? i)} label={String(props.state ?? "default")}>
                    <Drawn
                      components={[
                        { id: "root", component: name, ...props },
                        {
                          id: "content",
                          component: "Message",
                          text: "Plan A is ready for review.",
                          state: "delivered",
                        },
                        { id: "header", component: "TopBar", title: "Coalition 1" },
                        {
                          id: "dock",
                          component: "AgentDock",
                          agent: "a1",
                          messages: [{ text: "Your limits stay private." }],
                        },
                        { id: "tray", component: "ConsentTray", requests: [] },
                      ]}
                      data={{ stage: "Decide" }}
                    />
                  </State>
                ))}
              </div>
            </Cell>
          ))}
        </Family>
      ))}
    </div>
  );
}
function variants(name: string) {
  const base = examples[name] ?? {};
  const states: Record<string, string[]> = {
    Message: ["sending", "delivered", "seen", "failed", "redacted", "blocked"],
    ToolCall: ["running", "done", "failed"],
    AgentStatus: ["listening", "answering", "needs-you", "paused", "offline"],
  };
  return states[name]?.map((state) => ({ ...base, state })) ?? [base];
}
