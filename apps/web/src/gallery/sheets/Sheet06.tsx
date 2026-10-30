// SPDX-License-Identifier: Apache-2.0
import { examples } from "../../components/f06/examples";
import { panelProps } from "../../components/f06/panel-props";
import { Family } from "../Cell";
import { One } from "../Drawn";
import "../../styles/f06.css";

export { examples };

const sections = [
  {
    n: "06a",
    title: "Needs, offers and answers",
    names: ["NeedCard", "OfferCard", "AnswerCard", "MatchView"],
  },
  {
    n: "06b",
    title: "Tasks, dependencies and the schedule",
    names: ["TaskCard", "Gantt", "DependencyGraph", "Checklist", "Timeline"],
  },
  {
    n: "06c",
    title: "Plans, trade-offs, load and money",
    names: [
      "PlanCompare",
      "AssignmentRow",
      "TensionCard",
      "ObjectiveBars",
      "FairnessMeter",
      "CostSplit",
    ],
  },
];
const titles: Record<string, string> = {
  NeedCard: "lifecycle",
  OfferCard: "lifecycle",
  AnswerCard: "vault answers",
  MatchView: "need to offers",
  TaskCard: "status track",
  Gantt: "tasks over days",
  DependencyGraph: "what a change touches",
  Checklist: "steps of a task",
  Timeline: "commitments",
  PlanCompare: "universes side by side",
  AssignmentRow: "your part",
  TensionCard: "a real trade-off",
  ObjectiveBars: "objectives",
  FairnessMeter: "load vs share",
  CostSplit: "who pays, settle up",
};
const spans: Record<string, number> = {
  Gantt: 3,
  DependencyGraph: 2,
  PlanCompare: 3,
  TensionCard: 2,
};
export function Sheet06() {
  return (
    <div className="sheet f06-sheet" data-testid="sheet-06">
      <div className="sheet-head">
        <div>
          <div className="eyebrow">coalitionkit/v0_9 · family 06 · example data</div>
          <div className="sheet-title">Needs, offers, tasks and plans</div>
          <div className="sheet-sub">
            What people need and offer, how the Gardener turns them into tasks and plans, and how
            the trade-offs, the load and the money are shown before anyone decides.
          </div>
        </div>
        <div className="h-right">
          <span className="badge b-example">Example data</span>
          <span className="scope">need · offer · task · plan · tension</span>
        </div>
      </div>
      {sections.map((section) => (
        <Family key={section.n} n={section.n} title={section.title}>
          {section.names.map((name) => (
            <div
              key={name}
              className={`cell${spans[name] ? ` span${spans[name]}` : ""}`}
              data-panel={name}
            >
              <div className="head">
                <span className="cell-name">
                  {name} · {titles[name]}
                </span>
                {name === "AnswerCard" && <span className="h-right badge b-vault">Vault</span>}
              </div>
              <div className="demo">
                {examples[name]?.map((example) => (
                  <One
                    key={example.state}
                    component={name}
                    props={example.props}
                    data={{ current: "Decide" }}
                  />
                ))}
              </div>
              <div className="props">
                {panelProps[name] ?? "objectives[] {name, value, unit, better}"}
              </div>
            </div>
          ))}
        </Family>
      ))}
    </div>
  );
}
