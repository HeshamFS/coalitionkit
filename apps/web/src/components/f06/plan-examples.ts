// SPDX-License-Identifier: Apache-2.0
const bound = (value: number) => ({ value, event_ref: "example:1" });
const objectives = (result: string, progress: number, cost: number, load: number) => [
  {
    name: "Results by",
    value: bound(progress),
    display: result,
    scale: bound(100),
    better: "higher",
  },
  {
    name: "Cost",
    value: bound(cost),
    unit: "€",
    scale: bound(cost === 110 ? 275 : 287),
    better: "lower",
  },
  {
    name: "Max load",
    value: bound(load),
    unit: "%",
    scale: bound(100),
    better: "lower",
    tone: load > 50 ? "warn" : undefined,
  },
];
export const planExamples = [
  {
    state: "default",
    props: {
      plans: [
        {
          id: "a",
          label: "Plan A",
          description: "Plan A · send Wednesday",
          subject: { kind: "plan", id: "a", revision: bound(2) },
          objectives: objectives("Mon", 92, 158, 41),
          assignments: [
            { participant: "Member A" },
            { participant: "Member B" },
            { participant: "Member C" },
          ],
          highlight: true,
          tag: { label: "fastest", kind: "signed" },
          note: "6 tasks · all 3 seats",
        },
        {
          id: "b",
          label: "Plan B",
          description: "Plan B · next week",
          subject: { kind: "plan", id: "b", revision: bound(2) },
          objectives: objectives("Mon+7", 45, 92, 40),
          assignments: [
            { participant: "Member A" },
            { participant: "Member B" },
            { participant: "Member C" },
          ],
          tag: { label: "cheapest", kind: "estimate" },
          note: "6 tasks · slower transfer",
        },
      ],
      rejected: [
        {
          plan: {
            id: "c",
            label: "Plan C",
            description: "Plan C · without Seat C",
            objectives: objectives("Sat", 70, 110, 72),
            tag: { label: "misses goal", kind: "estimate" },
          },
          reason: "No model run · breaks rule 3 (load over half)",
        },
      ],
      proposal_set_id: "set1",
      decision_deadline: "2031-06-05T16:00:00Z",
    },
  },
];

const compared = planExamples[0]?.props;
export const objectiveExamples = [
  ...(compared?.plans ?? []).map((plan) => ({
    state: plan.id,
    props: { objectives: plan.objectives },
  })),
  ...(compared?.rejected ?? []).map(({ plan }) => ({
    state: plan.id,
    props: { objectives: plan.objectives.map((objective) => ({ ...objective, muted: true })) },
  })),
];
