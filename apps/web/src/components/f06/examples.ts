// SPDX-License-Identifier: Apache-2.0
import { planningExamples } from "./planning-examples";
export const examples: Record<string, { state: string; props: Record<string, unknown> }[]> = {
  NeedCard: [
    {
      state: "open",
      props: {
        need_id: "n1",
        owner: "Member B",
        text: "Resource 1 to Member A by Wed 22:00",
        constraints: ["by Wednesday"],
        by: "2030-06-05T12:00:00Z",
        state: "open",
        offers: { value: 0, event_ref: "example:1" },
      },
    },
    {
      state: "matched",
      props: {
        need_id: "n1",
        owner: "Member B",
        text: "Resource 1 to Member A by Wed 22:00",
        constraints: ["by Wednesday"],
        by: "2030-06-05T12:00:00Z",
        state: "matched",
        offers: { value: 0, event_ref: "example:1" },
      },
    },
    {
      state: "fulfilled",
      props: {
        need_id: "n1",
        owner: "Member B",
        text: "Resource 1 to Member A by Wed 22:00",
        constraints: ["by Wednesday"],
        by: "2030-06-05T12:00:00Z",
        state: "fulfilled",
        offers: { value: 0, event_ref: "example:1" },
      },
    },
    {
      state: "withdrawn",
      props: {
        need_id: "n1",
        owner: "Member B",
        text: "Resource 1 to Member A by Wed 22:00",
        constraints: ["by Wednesday"],
        by: "2030-06-05T12:00:00Z",
        state: "withdrawn",
        offers: { value: 0, event_ref: "example:1" },
      },
    },
  ],
  OfferCard: [
    {
      state: "open",
      props: {
        offer_id: "o1",
        what: "Resource 1, Wed 16:00",
        target: "need",
        cost: { amount: { value: 38, event_ref: "example:1" }, kind: "quote", unit: "\u20ac" },
        conditions: ["Available Wednesday"],
        expires: "2030-06-05T12:00:00Z",
        state: "open",
        scope: "coalition",
      },
    },
    {
      state: "accepted",
      props: {
        offer_id: "o1",
        what: "Resource 1, Wed 16:00",
        target: "need",
        cost: { amount: { value: 38, event_ref: "example:1" }, kind: "quote", unit: "\u20ac" },
        conditions: ["Available Wednesday"],
        expires: "2030-06-05T12:00:00Z",
        state: "accepted",
        scope: "coalition",
      },
    },
    {
      state: "expired",
      props: {
        offer_id: "o1",
        what: "Resource 1, Wed 16:00",
        target: "need",
        cost: { amount: { value: 38, event_ref: "example:1" }, kind: "quote", unit: "\u20ac" },
        conditions: ["Available Wednesday"],
        expires: "2030-06-05T12:00:00Z",
        state: "expired",
        scope: "coalition",
      },
    },
    {
      state: "withdrawn",
      props: {
        offer_id: "o1",
        what: "Resource 1, Wed 16:00",
        target: "need",
        cost: { amount: { value: 38, event_ref: "example:1" }, kind: "quote", unit: "\u20ac" },
        conditions: ["Available Wednesday"],
        expires: "2030-06-05T12:00:00Z",
        state: "withdrawn",
        scope: "coalition",
      },
    },
  ],
  AnswerCard: [
    {
      state: "bool",
      props: {
        query: "Can Resource 1 be ready by Wed 16:00?",
        kind: "bool",
        answer: true,
        from: "Member B vault",
      },
    },
    {
      state: "number-range",
      props: {
        query: "Can Resource 1 be ready by Wed 16:00?",
        kind: "number-range",
        answer: {
          min: { value: 6, event_ref: "example:1" },
          max: { value: 10, event_ref: "example:1" },
          unit: "h",
        },
        from: "Member B vault",
      },
    },
    {
      state: "choice",
      props: {
        query: "Can Resource 1 be ready by Wed 16:00?",
        kind: "choice",
        answer: "Option 2",
        from: "Member B vault",
      },
    },
    {
      state: "waiting",
      props: {
        query: "Can Resource 1 be ready by Wed 16:00?",
        kind: "bool",
        from: "Member B vault",
      },
    },
    {
      state: "declined",
      props: {
        query: "Can Resource 1 be ready by Wed 16:00?",
        kind: "bool",
        answer: null,
        from: "Member B vault",
      },
    },
  ],
  MatchView: [
    {
      state: "default",
      props: {
        need: "Resource 1",
        chosen: "Thu 09:00",
        offers: [
          { offer: "Thu 09:00", fit: "best fit", reasons: ["earliest", "no cost"] },
          { offer: "Fri 14:00", fit: "possible", reasons: ["\u20ac120"] },
          { offer: "Sat 10:00", fit: "fails", blockedBy: "late", reasons: [] },
        ],
      },
    },
  ],
  TaskCard: [
    {
      state: "open",
      props: {
        task_id: "t3",
        title: "Process Resource 1",
        assignee: "Member A",
        window: { start: "Thu 09:00", end: "10:30" },
        status: "open",
        deps: { waitsFor: ["t2"], unblocks: ["t4", "t5"] },
      },
    },
    {
      state: "negotiating",
      props: {
        task_id: "t3",
        title: "Process Resource 1",
        assignee: "Member A",
        window: { start: "Thu 09:00", end: "10:30" },
        status: "negotiating",
        deps: { waitsFor: ["t2"], unblocks: ["t4", "t5"] },
      },
    },
    {
      state: "proposed",
      props: {
        task_id: "t3",
        title: "Process Resource 1",
        assignee: "Member A",
        window: { start: "Thu 09:00", end: "10:30" },
        status: "proposed",
        deps: { waitsFor: ["t2"], unblocks: ["t4", "t5"] },
      },
    },
    {
      state: "decided",
      props: {
        task_id: "t3",
        title: "Process Resource 1",
        assignee: "Member A",
        window: { start: "Thu 09:00", end: "10:30" },
        status: "decided",
        deps: { waitsFor: ["t2"], unblocks: ["t4", "t5"] },
      },
    },
    {
      state: "committed",
      props: {
        task_id: "t3",
        title: "Process Resource 1",
        assignee: "Member A",
        window: { start: "Thu 09:00", end: "10:30" },
        status: "committed",
        deps: { waitsFor: ["t2"], unblocks: ["t4", "t5"] },
      },
    },
    {
      state: "done",
      props: {
        task_id: "t3",
        title: "Process Resource 1",
        assignee: "Member A",
        window: { start: "Thu 09:00", end: "10:30" },
        status: "done",
        deps: { waitsFor: ["t2"], unblocks: ["t4", "t5"] },
      },
    },
    {
      state: "withdrawn",
      props: {
        task_id: "t3",
        title: "Process Resource 1",
        assignee: "Member A",
        window: { start: "Thu 09:00", end: "10:30" },
        status: "withdrawn",
        deps: { waitsFor: ["t2"], unblocks: ["t4", "t5"] },
      },
    },
  ],
  Gantt: [
    {
      state: "default",
      props: {
        rows: [
          {
            task: "t1",
            assignee: "Member A",
            start: "2030-06-03T09:00:00Z",
            end: "2030-06-03T19:00:00Z",
            status: "done",
          },
          {
            task: "t2",
            assignee: "Member B",
            start: "2030-06-04T09:00:00Z",
            end: "2030-06-04T19:00:00Z",
            status: "done",
          },
          {
            task: "t3",
            assignee: "Member C",
            start: "2030-06-05T09:00:00Z",
            end: "2030-06-05T19:00:00Z",
            status: "committed",
          },
          {
            task: "t4",
            assignee: "Member A",
            start: "2030-06-06T09:00:00Z",
            end: "2030-06-06T19:00:00Z",
            status: "committed",
          },
          {
            task: "t5",
            assignee: "Member B",
            start: "2030-06-07T09:00:00Z",
            end: "2030-06-07T19:00:00Z",
            status: "committed",
          },
          {
            task: "t6",
            assignee: "Member C",
            start: "2030-06-08T09:00:00Z",
            end: "2030-06-08T19:00:00Z",
            status: "committed",
          },
        ],
        now: "2030-06-05T11:20:00Z",
        deadlines: ["Mon 12:00"],
        criticalPath: ["t2", "t3", "t5", "t6"],
        zoom: "days",
      },
    },
  ],
  DependencyGraph: [
    {
      state: "default",
      props: {
        nodes: [
          { task: "t1", status: "done" },
          { task: "t2", status: "negotiating" },
          { task: "t3", status: "negotiating" },
          { task: "t4", status: "negotiating" },
          { task: "t5", status: "negotiating" },
          { task: "t6", status: "negotiating" },
          { task: "t7", status: "negotiating" },
        ],
        edges: [
          { from: "t1", to: "t2" },
          { from: "t2", to: "t3" },
          { from: "t3", to: "t4" },
          { from: "t3", to: "t5" },
          { from: "t5", to: "t6" },
          { from: "t4", to: "t7" },
        ],
        changed: "t2",
        invalidated: ["t3", "t4", "t5", "t6"],
      },
    },
  ],
  Checklist: [
    {
      state: "default",
      props: {
        items: [
          { text: "Receive resource", done: true, by: "self", evidence: "" },
          { text: "Record evidence", done: true, by: "self", evidence: "" },
          { text: "Start process", done: false, by: "self", evidence: "live" },
          { text: "Hold 45 min", done: false, by: "self", evidence: "" },
          { text: "Complete and log", done: false, by: "self", evidence: "" },
        ],
      },
    },
  ],
  Timeline: [
    {
      state: "default",
      props: {
        items: [
          { start: "Tue 3", title: "Task 1", assignee: "Member A", state: "done" },
          { start: "Wed 4", title: "Task 2", assignee: "Member A", state: "done" },
          { start: "Thu 5", title: "Task 3", assignee: "Member A", state: "now" },
          { start: "Fri 6", title: "Task 4", assignee: "Member A", state: "next" },
        ],
        now: "2030-06-05T12:00:00Z",
      },
    },
  ],
  PlanCompare: [
    {
      state: "default",
      props: {
        plans: [
          {
            id: "a",
            label: "Plan A",
            subject: { kind: "plan", id: "a", revision: { value: 2, event_ref: "example:1" } },
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
            assignments: [],
            highlight: true,
          },
          {
            id: "b",
            label: "Plan B",
            subject: { kind: "plan", id: "b", revision: { value: 2, event_ref: "example:1" } },
            objectives: [
              {
                name: "Cost",
                value: { value: 92, event_ref: "example:1" },
                unit: "\u20ac",
                better: "lower",
              },
              {
                name: "Max load",
                value: { value: 40, event_ref: "example:1" },
                unit: "%",
                better: "lower",
              },
            ],
            assignments: [],
            highlight: false,
          },
        ],
        rejected: [
          {
            plan: {
              id: "c",
              label: "Plan C",
              objectives: [
                {
                  name: "Cost",
                  value: { value: 110, event_ref: "example:1" },
                  unit: "\u20ac",
                  better: "lower",
                },
                {
                  name: "Max load",
                  value: { value: 72, event_ref: "example:1" },
                  unit: "%",
                  better: "lower",
                },
              ],
            },
            reason: "Misses goal \u00b7 load over half",
          },
        ],
        proposal_set_id: "set1",
        decision_deadline: "2030-06-05T12:00:00Z",
      },
    },
  ],
  ...planningExamples,
};
