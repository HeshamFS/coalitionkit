// SPDX-License-Identifier: Apache-2.0
import { examples as allExamples } from "../../components/f06/examples";
import { panelProps } from "../../components/f06/panel-props";
import { objectiveExamples } from "../../components/f06/plan-examples";
import { ObjectiveBarsRenderer, type Plan } from "../../components/f06/plans";
import { Family } from "../Cell";
import { One } from "../Drawn";
import "../../styles/f06.css";

// The sheet inventory includes only the drawn states; ObjectiveBars lives inside PlanCompare.
export const examples = {
  ...allExamples,
  TaskCard:
    allExamples.TaskCard?.filter((example) =>
      ["decided", "done", "withdrawn"].includes(example.state),
    ) ?? [],
  ObjectiveBars: objectiveExamples,
} as typeof allExamples;

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
    names: ["PlanCompare", "AssignmentRow", "TensionCard", "FairnessMeter", "CostSplit"],
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
function drawObjectives(plan: Plan, muted = false) {
  return (
    <One
      component="ObjectiveBars"
      props={{ objectives: plan.objectives.map((objective) => ({ ...objective, muted })) }}
    />
  );
}
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
                {name === "Gantt" && (
                  <>
                    <span className="h-right door">
                      <span>wide</span>
                    </span>
                    <span className="badge b-model">Plan A</span>
                  </>
                )}
                {name === "DependencyGraph" && (
                  <span className="h-right badge b-measured">from task deps</span>
                )}
                {name === "Timeline" && (
                  <span className="h-right door">
                    <span>compact</span>
                  </span>
                )}
                {name === "PlanCompare" && (
                  <span className="h-right">
                    <span className="badge b-model">Gardener</span>
                    <span className="badge b-signed">Steward passed</span>
                  </span>
                )}
                {name === "TensionCard" && <span className="h-right tag t-needs">Needs you</span>}
                {name === "FairnessMeter" && (
                  <span className="h-right badge b-measured">computed</span>
                )}
                {name === "CostSplit" && <span className="h-right badge b-estimate">Estimate</span>}
              </div>
              <div className="demo">
                {examples[name]?.map((example) =>
                  name === "PlanCompare" ? (
                    <ObjectiveBarsRenderer.Provider key={example.state} value={drawObjectives}>
                      <One component={name} props={example.props} />
                    </ObjectiveBarsRenderer.Provider>
                  ) : (
                    <One
                      key={example.state}
                      component={name}
                      props={example.props}
                      data={{ current: "Decide" }}
                    />
                  ),
                )}
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
