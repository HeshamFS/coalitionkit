// SPDX-License-Identifier: Apache-2.0
import { planExamples } from "./plan-examples";
export const planningExamples: Record<string, { state: string; props: Record<string, unknown> }[]> =
  {
    PlanCompare: planExamples,
    AssignmentRow: [
      {
        state: "default",
        props: {
          assignments: [
            {
              task: "t2",
              title: "Transfer to A",
              window: "Wed 16:00",
              plan: "Plan A",
              total: { value: 34, event_ref: "example:1" },
            },
            { task: "t4", title: "Return", window: "Thu 12:00" },
            { task: "t5", title: "Review", window: "Fri 14:00" },
          ],
          hours: { value: 9, event_ref: "example:1" },
          share: { value: 26, event_ref: "example:1" },
          fit: "fits your calendar",
        },
      },
    ],
    TensionCard: [
      {
        state: "default",
        props: {
          tension_id: "tension1",
          task_ids: ["t2", "t3"],
          subject: {
            kind: "tension_option",
            id: "tension1",
            revision: { value: 2, event_ref: "example:1" },
          },
          options: [
            {
              id: "a",
              summary: "Fast or cheap? The plans differ by a week and €66.",
              label: "Results Monday",
              tradeoffs: ["+ €66 for the express transfer", "Member B carries the cost"],
            },
            {
              id: "b",
              label: "Results a week later",
              tradeoffs: ["saves \u20ac66", "Resource must be reserved again"],
            },
          ],
          deciders: ["Member A", "Member B", "Member C"],
          answered: { value: 1, event_ref: "example:1" },
          decision_deadline: "2031-06-05T16:00:00Z",
        },
      },
    ],
    ObjectiveBars: [
      {
        state: "default",
        props: {
          objectives: [
            {
              name: "Cost",
              value: { value: 158, event_ref: "example:1" },
              unit: "\u20ac",
              better: "lower",
            },
            {
              name: "Max load",
              value: { value: 41, event_ref: "example:1" },
              unit: "%",
              better: "lower",
            },
          ],
        },
      },
    ],
    FairnessMeter: [
      {
        state: "default",
        props: {
          rows: [
            {
              participant: "Member A",
              rule: "charter rule 3",
              hours: { value: 14, event_ref: "example:1" },
              share: { value: 41, event_ref: "example:1" },
              agreedShare: { value: 41, event_ref: "example:1" },
            },
            {
              participant: "Member B",
              hours: { value: 9, event_ref: "example:1" },
              share: { value: 26, event_ref: "example:1" },
              agreedShare: { value: 26, event_ref: "example:1" },
            },
            {
              participant: "Member C",
              hours: { value: 11, event_ref: "example:1" },
              share: { value: 33, event_ref: "example:1" },
              agreedShare: { value: 33, event_ref: "example:1" },
            },
          ],
          cap: { value: 50, event_ref: "example:1" },
        },
      },
    ],
    CostSplit: [
      {
        state: "default",
        props: {
          items: [
            {
              label: "Resource 1",
              payer: "Member B",
              amount: { value: 76, event_ref: "example:1" },
              kind: "estimate",
            },
            {
              label: "Resource 2",
              payer: "Member A",
              amount: { value: 42, event_ref: "example:1" },
              kind: "estimate",
            },
            {
              label: "Resource 3",
              payer: "Member C",
              amount: { value: 40, event_ref: "example:1" },
              kind: "estimate",
            },
          ],
          rule: "even",
          settlements: ["Even split \u20ac52.67 each", "B gets €23.33 back"],
        },
      },
    ],
  };
