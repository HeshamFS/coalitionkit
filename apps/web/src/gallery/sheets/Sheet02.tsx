// SPDX-License-Identifier: Apache-2.0
import { examples, groups, labels } from "../../components/f02/examples";
import { Family } from "../Cell";
import { Drawn } from "../Drawn";

const titles: Record<string, string> = {
  EntryComposer: "EntryComposer · the empty table",
  InviteCard: "InviteCard · QR",
  JoinScreen: "JoinScreen · charter accept",
  MessageDoor: "MessageDoor · WhatsApp",
  LensCard: "LensCard · glasses",
  VoiceTurn: "VoiceDoor · spoken turn",
  SplitView: "SplitView · list and detail",
  PageHeader: "PageHeader · Breadcrumbs",
  ConsentTray: "ConsentTray · docked",
  WiringDrawer: "WiringDrawer · the message behind it",
  AccountMenu: "AccountMenu · Settings",
  BoardTemplate: "BoardTemplate · columns by status",
};
const doors: Record<string, string[]> = {
  RoomShell: ["wide"],
  EntryComposer: ["wide", "compact"],
  PhoneShell: ["compact"],
  MessageDoor: ["message"],
  LensCard: ["lens"],
  VoiceTurn: ["voice"],
  ConsentTray: ["wide", "compact"],
  WiringDrawer: ["wide"],
};
export function Sheet02() {
  return (
    <div className="ck-sheet f02-sheet" data-testid="sheet-02">
      <div className="sheet-head">
        <div>
          <div className="eyebrow">coalitionkit/v0_9 · family 02 · example data</div>
          <h1 className="sheet-title">Shell, doors and templates</h1>
          <div className="sheet-sub">
            The thin fixed frame, the four doors a surface can open through, and the containers
            agents compose into. Everything inside the frame is generated.
          </div>
        </div>
      </div>
      {groups.map(([heading, names], index) => (
        <Family
          key={String(heading)}
          n={`02${String.fromCharCode(97 + index)}`}
          title={String(heading)}
        >
          {(index === 0 ? ["RoomShell"] : (names as string[])).map((name) => (
            <div
              className={`cell${name === "RoomShell" ? " span4" : ["EntryComposer", "ConsentTray", "WiringDrawer", "BoardTemplate"].includes(name) ? " span2" : ""}`}
              data-panel={name}
              key={name}
            >
              <div className="f02-panel-head">
                <span className="cell-name">{titles[name] ?? name}</span>
                <div className="door">
                  {doors[name]?.map((door) => (
                    <span key={door}>{door}</span>
                  ))}
                </div>
              </div>
              <Drawn
                components={[
                  {
                    id: "root",
                    component: name,
                    ...examples[name],
                    ...(name === "ConsentTray"
                      ? {
                          requests: [
                            {
                              kind: "plan",
                              label: "Plan A · work together",
                              deadline: "18 min",
                              subject: {
                                kind: "plan",
                                id: "p1",
                                revision: { value: 2, event_ref: "example:44" },
                              },
                            },
                            {
                              kind: "commitment",
                              label: "Your commitment: book Resource 1",
                              deadline: "today",
                              subject: {
                                kind: "commitment",
                                id: "c1",
                                revision: { value: 1, event_ref: "example:44" },
                              },
                            },
                            {
                              kind: "charter",
                              label: "Revision 3: budget raised to €2",
                              subject: {
                                kind: "charter",
                                id: "c2",
                                revision: { value: 3, event_ref: "example:44" },
                              },
                            },
                          ],
                        }
                      : {}),
                  },
                  {
                    id: "content",
                    component: "Column",
                    gap: "8",
                    children: ["plan", "task", "offers"],
                  },
                  {
                    id: "plan",
                    component: "Card",
                    title: "Plan A · work together",
                    status: "needs-you",
                    fields: [
                      { label: "", value: "07:10 start, 3 places · Resource 1 · Task 3 at 22:30" },
                    ],
                  },
                  {
                    id: "task",
                    component: "Card",
                    title: "Task 3",
                    status: "changed",
                    tone: "live",
                    fields: [{ label: "", value: "starts 22:45 · 3 places · ≈ €14 each" }],
                  },
                  {
                    id: "offers",
                    component: "Card",
                    title: "Your offers",
                    fields: [{ label: "", value: "Resource 1 · Resource 2" }],
                  },
                  {
                    id: "header",
                    component: "TopBar",
                    title: "Coalition 1",
                    stage: { path: "/stage" },
                    presence: examples.TopBar?.presence,
                  },
                  { id: "dock", component: "AgentDock", ...examples.AgentDock },
                  { id: "tray", component: "ConsentTray", ...examples.ConsentTray },
                ]}
                data={{ stage: "Decide" }}
              />
              <div className="props">{labels[name]?.props}</div>
              {name === "EntryComposer" && (
                <div className="evts">→ coalition.create(goal, pack?)</div>
              )}
            </div>
          ))}
        </Family>
      ))}
    </div>
  );
}
