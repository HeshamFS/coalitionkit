// SPDX-License-Identifier: Apache-2.0
import { Cell, Family, State } from "../Cell";
import { One } from "../Drawn";
import "../../styles/f05.css";
import { examples } from "../../components/f05/examples";

export { examples };
export function Sheet05() {
  return (
    <div className="sheet" data-testid="sheet-05">
      <div className="sheet-head">
        <div>
          <div className="eyebrow">coalitionkit/v0_9 · family 05 · example data</div>
          <div className="sheet-title">Coalition and people</div>
        </div>
      </div>
      <Family n="05a" title="The coalition at a glance">
        <Cell
          name="CoalitionHeader"
          props={
            "budget \u00b7 counts \u00b7 goal \u00b7 pack \u00b7 revision \u00b7 title \u00b7 yourState"
          }
          events={"charter.open"}
          span={2}
        >
          {examples.CoalitionHeader?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="CoalitionHeader" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}

          {examples.StageTrack?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="StageTrack" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}
        </Cell>

        <Cell
          name="SeatRing"
          props={"goal \u00b7 openSeats \u00b7 seats"}
          events={"seat.open(participant)"}
        >
          {examples.SeatRing?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="SeatRing" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}
        </Cell>
        <Cell
          name="CharterCard"
          props={"revision \u00b7 roles \u00b7 rules \u00b7 signedBy"}
          events={"charter.history"}
        >
          {examples.CharterCard?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="CharterCard" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}
        </Cell>
      </Family>
      <Family n="05b" title="People, agents and who acts for whom">
        <Cell
          name="ParticipantCard"
          props={"act \u00b7 capabilities \u00b7 participant \u00b7 roles \u00b7 seat \u00b7 state"}
          events={"participant.open"}
          span={2}
        >
          {examples.ParticipantCard?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="ParticipantCard" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}
        </Cell>
        <Cell
          name="ActsForGraph"
          props={"acting \u00b7 agents \u00b7 people"}
          events={"agent.inspect(card)"}
          span={2}
        >
          {examples.ActsForGraph?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="ActsForGraph" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}
        </Cell>
        <Cell name="VendorBadge" props={"framework \u00b7 transport"} events={"display only"}>
          {examples.VendorBadge?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="VendorBadge" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}

          {examples.AgentPresence?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="AgentPresence" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}
        </Cell>

        <Cell name="RoleChip" props={"open \u00b7 role"} events={"display only"}>
          {examples.RoleChip?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="RoleChip" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}

          {examples.RoleMatrix?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="RoleMatrix" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}
        </Cell>

        <Cell name="Roster" props={"members"} events={"member.remind(participant)"} span={2}>
          {examples.Roster?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="Roster" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}
        </Cell>
        <Cell name="PackChip" props={"pack"} events={"pack.open"}>
          {examples.PackChip?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="PackChip" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}
        </Cell>
        <Cell name="LeaveControl" props={"consequences"} events={"coalition.leave"}>
          {examples.LeaveControl?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="LeaveControl" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}
        </Cell>
        <Cell
          name="InviteList"
          props={"invitations \u00b7 openSeats"}
          events={"invite.send \u00b7 invite.revoke"}
          span={2}
        >
          {examples.InviteList?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="InviteList" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}
        </Cell>
      </Family>
    </div>
  );
}
