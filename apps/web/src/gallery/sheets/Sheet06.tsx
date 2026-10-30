// SPDX-License-Identifier: Apache-2.0
import { Cell, Family, State } from "../Cell";
import { One } from "../Drawn";
import "../../styles/f06.css";
import { examples } from "../../components/f06/examples";

export { examples };
export function Sheet06() {
  return (
    <div className="sheet" data-testid="sheet-06">
      <div className="sheet-head">
        <div>
          <div className="eyebrow">coalitionkit/v0_9 · family 06 · example data</div>
          <div className="sheet-title">Needs, offers, tasks and plans</div>
        </div>
      </div>
      <Family n="06a" title="Needs, offers and answers">
        <Cell
          name="NeedCard"
          props={
            "by \u00b7 constraints \u00b7 need_id \u00b7 offers \u00b7 owner \u00b7 state \u00b7 text"
          }
          events={"need.open \u00b7 need.withdraw"}
        >
          {examples.NeedCard?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="NeedCard" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}
        </Cell>
        <Cell
          name="OfferCard"
          props={
            "conditions \u00b7 cost \u00b7 expires \u00b7 offer_id \u00b7 scope \u00b7 state \u00b7 target \u00b7 what"
          }
          events={"offer.accept \u00b7 offer.ask \u00b7 offer.withdraw"}
        >
          {examples.OfferCard?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="OfferCard" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}
        </Cell>
        <Cell
          name="AnswerCard"
          props={"answer \u00b7 from \u00b7 kind \u00b7 query \u00b7 task_id"}
          events={"display only"}
        >
          {examples.AnswerCard?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="AnswerCard" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}
        </Cell>
        <Cell
          name="MatchView"
          props={"chosen \u00b7 need \u00b7 offers"}
          events={"match.inspect(offer)"}
        >
          {examples.MatchView?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="MatchView" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}
        </Cell>
      </Family>
      <Family n="06b" title="Tasks, dependencies and the schedule">
        <Cell
          name="TaskCard"
          props={
            "assignee \u00b7 deps \u00b7 evidence \u00b7 status \u00b7 task_id \u00b7 title \u00b7 window"
          }
          events={"task.open \u00b7 task.done"}
        >
          {examples.TaskCard?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="TaskCard" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}
        </Cell>
        <Cell
          name="Gantt"
          props={"criticalPath \u00b7 deadlines \u00b7 now \u00b7 rows \u00b7 zoom"}
          events={"task.open(id)"}
          span={3}
        >
          {examples.Gantt?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="Gantt" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}
        </Cell>
        <Cell
          name="DependencyGraph"
          props={"changed \u00b7 edges \u00b7 invalidated \u00b7 nodes"}
          events={"task.open(id)"}
          span={2}
        >
          {examples.DependencyGraph?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="DependencyGraph" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}
        </Cell>
        <Cell name="Checklist" props={"items"} events={"item.toggle (owner only)"}>
          {examples.Checklist?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="Checklist" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}
        </Cell>
        <Cell name="Timeline" props={"items \u00b7 now"} events={"display only"}>
          {examples.Timeline?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="Timeline" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}
        </Cell>
      </Family>
      <Family n="06c" title="Plans, trade-offs, load and cost">
        <Cell
          name="PlanCompare"
          props={"decision_deadline \u00b7 plans \u00b7 proposal_set_id \u00b7 rejected"}
          events={"plan.decide(id) \u2192 consent \u00b7 plan.details(id)"}
          span={3}
        >
          {examples.PlanCompare?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="PlanCompare" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}
        </Cell>
        <Cell
          name="AssignmentRow"
          props={"assignments \u00b7 fit \u00b7 hours \u00b7 share"}
          events={"display only"}
        >
          {examples.AssignmentRow?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="AssignmentRow" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}
        </Cell>
        <Cell
          name="TensionCard"
          props={
            "answered \u00b7 deciders \u00b7 decision_deadline \u00b7 options \u00b7 subject \u00b7 task_ids \u00b7 tension_id"
          }
          events={"tension.choose(option) \u2192 consent"}
          span={2}
        >
          {examples.TensionCard?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="TensionCard" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}
        </Cell>
        <Cell name="ObjectiveBars" props={"objectives"} events={"display only"}>
          {examples.ObjectiveBars?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="ObjectiveBars" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}
        </Cell>
        <Cell name="FairnessMeter" props={"cap \u00b7 rows"} events={"display only"}>
          {examples.FairnessMeter?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="FairnessMeter" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}
        </Cell>
        <Cell
          name="CostSplit"
          props={"items \u00b7 rule \u00b7 settlements"}
          events={"display only"}
        >
          {examples.CostSplit?.map((e) => (
            <State key={e.state} label={e.state}>
              <One component="CostSplit" props={e.props} data={{ current: "Decide" }} />
            </State>
          ))}
        </Cell>
      </Family>
    </div>
  );
}
