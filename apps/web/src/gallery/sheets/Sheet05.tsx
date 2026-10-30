// SPDX-License-Identifier: Apache-2.0
import "./Sheet05.css";
import type { ReactNode } from "react";
import { examples } from "../../components/f05/examples";
import { Family } from "../Cell";
import { One } from "../Drawn";
import "../../styles/f05.css";

export { examples };

const doors: Record<string, string[]> = {
  CoalitionHeader: ["wide", "compact", "lens"],
  SeatRing: ["wide", "lens"],
  MapView: ["wide", "compact"],
  RouteCard: ["compact", "lens"],
  ArrivalCard: ["lens", "message"],
  CalendarWeek: ["wide"],
  AgendaList: ["compact", "voice"],
};
export function Panel({
  name,
  title,
  summary,
  span,
  events,
  children,
}: {
  name: string;
  title: string;
  summary: string;
  span?: boolean;
  events?: string;
  children: ReactNode;
}) {
  return (
    <div className={`cell${span ? " span2" : ""}`} data-component={name}>
      <div className="head">
        <span className="cell-name">{title}</span>
        {doors[name] && (
          <span className="h-right door">
            {doors[name].map((door) => (
              <span key={door}>{door}</span>
            ))}
          </span>
        )}
        {name === "ActsForGraph" && (
          <span className="h-right badge b-signed">from signed joins</span>
        )}
      </div>
      <div className={`demo panel-${name}`}>{children}</div>
      <div className="props">{summary}</div>
      {events && <div className="evts">{events}</div>}
    </div>
  );
}
function Demo({ name }: { name: string }) {
  return (
    <>
      {examples[name]?.map((e) => (
        <One
          key={`${e.state}-${JSON.stringify(e.props)}`}
          component={name}
          props={e.props}
          data={{ current: "Decide" }}
        />
      ))}
    </>
  );
}
export function Sheet05() {
  return (
    <div className="sheet f05-sheet" data-testid="sheet-05">
      <div className="sheet-head">
        <div>
          <div className="eyebrow">coalitionkit/v0_9 · family 05 · example data</div>
          <div className="sheet-title">Coalition and people</div>
          <div className="sheet-sub">
            Who is in the room, who acts for whom, what they hold, and the rules they all signed.
            People and their agents are always shown as two different things.
          </div>
        </div>
        <div className="h-right">
          <span className="badge b-example">Example data</span>
          <span className="scope">members · roles · charter</span>
        </div>
      </div>
      <Family n="05a" title="The coalition at a glance">
        <Panel
          name="CoalitionHeader"
          title="CoalitionHeader · StageTrack"
          summary={
            "title \u00b7 goal \u00b7 pack? \u00b7 stage (7 steps, from host) \u00b7 stageProgress (deciders answered) \u00b7 counts \u00b7 budget {used, cap} \u00b7 charter revision \u00b7 your state tag"
          }
          span
        >
          <div className="card f05-overview">
            <Demo name="CoalitionHeader" />
            <Demo name="StageTrack" />
          </div>
        </Panel>
        <Panel
          name="SeatRing"
          title="SeatRing · the C"
          summary={
            "seats[] {participant, seat 1-5, role, state: acting | owes | idle | left} \u00b7 openSeats \u00b7 goal label \u00b7 max 7 seats drawn, then +n"
          }
        >
          <Demo name="SeatRing" />
        </Panel>
        <Panel
          name="CharterCard"
          title="CharterCard"
          summary={
            "rules[] {n, text} \u00b7 roles[] {name, min, max} \u00b7 deciders rule \u00b7 budget \u00b7 revision \u00b7 signedBy[] \u00b7 history (revisions with diffs)"
          }
        >
          <Demo name="CharterCard" />
        </Panel>
      </Family>
      <Family n="05b" title="People, agents and who acts for whom">
        <Panel
          name="ParticipantCard"
          title="ParticipantCard · every state"
          summary={
            "participant \u00b7 seat \u00b7 roles[] \u00b7 capabilities[] \u00b7 state: agreed | acting | owes | watcher | invited | left \u00b7 current act \u00b7 presence"
          }
          span
        >
          <Demo name="ParticipantCard" />
        </Panel>
        <Panel
          name="ActsForGraph"
          title="ActsForGraph · people, agents, keys"
          summary={
            "people[] {participant, ownerKid} \u00b7 agents[] {card, cardKid, vendor, runtime, actsFor} \u00b7 highlight: acting now \u00b7 edges from signed joins only"
          }
          span
        >
          <Demo name="ActsForGraph" />
        </Panel>
        <Panel
          name="VendorBadge"
          title="VendorBadge · AgentPresence"
          summary={
            "VendorBadge: transport (A2A | MCP | hosted | minted | local) \u00b7 framework label (never a logo) \u00b7 AgentPresence: live | idle | offline \u00b7 latency \u00b7 pinned key"
          }
        >
          <div className="f05-vendors">
            {[0, 2, 4].map((start) => (
              <div className="row" key={start}>
                {examples.VendorBadge?.slice(start, start + 2).map((example) => (
                  <One
                    key={String(example.props.framework)}
                    component="VendorBadge"
                    props={example.props}
                  />
                ))}
              </div>
            ))}
          </div>
          <div className="hr" />
          <Demo name="AgentPresence" />
        </Panel>
        <Panel
          name="RoleChip"
          title="RoleChip · RoleMatrix"
          summary={
            "roles[] {name, min, max, holders[]} \u00b7 rights matrix from the charter and spec's authorization table \u00b7 open roles shown dashed"
          }
        >
          <div className="row wrap">
            <Demo name="RoleChip" />
          </div>
          <Demo name="RoleMatrix" />
        </Panel>
        <Panel
          name="Roster"
          title="Roster · table of members"
          summary={
            "members[] {participant, roles, agents, acceptedRevision, load, state} \u00b7 sort \u00b7 rows with an old charter revision are flagged (C-21)"
          }
          span
        >
          <Demo name="Roster" />
        </Panel>
        <Panel
          name="PackChip"
          title="PackChip · pack card"
          summary={
            "pack {id, name, version, views[], policies[], author key} \u00b7 packs can't add block or quarantine rules"
          }
        >
          <Demo name="PackChip" />
        </Panel>
        <Panel
          name="LeaveControl"
          title="LeaveControl · RemoveRequest"
          summary={
            "consequences[] (computed by host) \u00b7 confirm via Modal \u00b7 \u2192 coalition.leave \u00b7 no rejoin"
          }
        >
          <Demo name="LeaveControl" />
        </Panel>
        <Panel
          name="InviteList"
          title="InviteList · seats still open"
          summary={
            "invitations[] {participant?, role, channel, sentAt, expires, state: invited | joined | expired | revoked} \u00b7 openSeats[] \u00b7 role change = new charter revision"
          }
          span
        >
          <Demo name="InviteList" />
        </Panel>
      </Family>
    </div>
  );
}
