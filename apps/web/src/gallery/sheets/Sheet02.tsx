// SPDX-License-Identifier: Apache-2.0
import "./Sheet02.css";
import { groups } from "../../components/f02/examples";
import { sheetLabels } from "../../components/f02/sheet-data";
import { sheetNodes } from "../../components/f02/sheet-nodes";
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
                {name === "RoomShell" && <span className="f02-example-badge">Fixed frame</span>}
              </div>
              <div className={name === "LensCard" ? "f02-lens-scene" : "f02-panel-demo"}>
                {name === "LensCard" && (
                  <svg viewBox="0 0 300 430" aria-hidden="true">
                    <rect x="40" y="230" width="220" height="140" fill="#2A323C" opacity=".55" />
                    <rect x="60" y="250" width="70" height="40" fill="#F5C542" opacity=".8" />
                    <text x="66" y="276" fontFamily="var(--font-mono)" fontSize="16" fill="#1B2436">
                      P12
                    </text>
                  </svg>
                )}
                <Drawn components={sheetNodes(name)} data={{ stage: "Decide" }} />
              </div>
              <div className="props">{sheetLabels[name]}</div>
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
