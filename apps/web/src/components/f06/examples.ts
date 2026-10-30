// SPDX-License-Identifier: Apache-2.0
import { planningExamples } from "./planning-examples";
export const examples: Record<string, { state: string; props: Record<string, unknown> }[]> = {
  NeedCard: [
    {
      state: "open",
      props: {
        need_id: "n1",
        owner: "Member B",
        text: "Resource to A by Wed 22:00",
        constraints: ["3 h old"],
        state: "open",
        offers: { value: 0, event_ref: "example:1" },
      },
    },
    {
      state: "matched",
      props: {
        need_id: "n2",
        owner: "Member A",
        text: "Resource slot, 45 min at 1 150",
        constraints: ["Gardener planning"],
        state: "matched",
        offers: { value: 2, event_ref: "example:2" },
      },
    },
    {
      state: "fulfilled",
      props: {
        need_id: "n3",
        owner: "Member C",
        text: "Review the processed resource",
        constraints: ["by Member B · Fri"],
        state: "fulfilled",
      },
    },
    {
      state: "withdrawn",
      props: { need_id: "n4", owner: "Member B", text: "Second transfer", state: "withdrawn" },
    },
  ],
  OfferCard: [
    {
      state: "quote",
      props: {
        offer_id: "o1",
        what: "Transfer, Wed 16:00",
        target: "need",
        cost: { amount: { value: 38, event_ref: "example:1" }, kind: "quote", unit: "€" },
        conditions: ['Member B · for need "resource to A"'],
        expires: "2030-06-05T18:00:00Z",
        state: "open",
        scope: "coalition",
      },
    },
    {
      state: "needs-you",
      props: {
        offer_id: "o2",
        what: "Run the process model",
        target: "task",
        conditions: ["Member C · 2D, results Mon · you accept or ask"],
        state: "open",
        scope: "coalition",
      },
    },
    {
      state: "private",
      props: {
        offer_id: "o3",
        what: "Spare resource",
        target: "need",
        conditions: ["only Member A and the host see it"],
        state: "open",
        scope: "private",
      },
    },
    {
      state: "expired",
      props: {
        offer_id: "o4",
        what: "Saturday resource slot",
        target: "need",
        expires: "2030-06-05T09:00:00Z",
        state: "expired",
        scope: "coalition",
      },
    },
  ],
  AnswerCard: [
    {
      state: "bool",
      props: {
        query: "Can the resource leave by Wed 16:00?",
        kind: "bool",
        answer: { value: true, event_ref: "example:39" },
        from: "Member B’s vault",
      },
    },
    {
      state: "number-range",
      props: {
        query: "Process hours needed?",
        kind: "number-range",
        answer: {
          min: { value: 6, event_ref: "example:1" },
          max: { value: 10, event_ref: "example:1" },
          unit: "h",
        },
        from: "Member C",
      },
    },
    {
      state: "choice",
      props: {
        query: "Mode?",
        kind: "choice",
        answer: { value: "Mode 2", choices: ["Mode 1", "Mode 2", "Mode 3"] },
        from: "Member A",
      },
    },
    {
      state: "waiting",
      props: {
        query: "Can you review on Friday?",
        kind: "bool",
        answer: { state: "waiting", waited: { value: 4, event_ref: "example:40" } },
        from: "Member B",
      },
    },
  ],
  MatchView: [
    {
      state: "default",
      props: {
        need: "Resource slot · Member A",
        chosen: "Thu 09:00",
        offers: [
          {
            offer: "Thu 09:00",
            fit: "best fit",
            description: "A resource · free",
            reasons: ["earliest", "no cost"],
          },
          {
            offer: "Fri 14:00",
            fit: "possible",
            description: "rented · €120",
            reasons: ["\u20ac120"],
          },
          { offer: "Sat 10:00", fit: "fails", blockedBy: "resource late", reasons: [] },
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
        task_id: "t1",
        title: "Prepare the resource",
        assignee: "Member A",
        status: "done",
        evidence: "photo + record",
      },
    },
    { state: "withdrawn", props: { task_id: "t6", title: "Second review", status: "withdrawn" } },
  ],
  Gantt: [
    {
      state: "default",
      props: {
        rows: [
          {
            task: "t1",
            title: "Prepare the resource",
            assignee: "Member A",
            start: "2031-06-03T00:00:00Z",
            end: "2031-06-03T20:09:36Z",
            status: "done",
          },
          {
            task: "t2",
            title: "Transfer to Member A",
            assignee: "Member B",
            start: "2031-06-04T03:21:36Z",
            end: "2031-06-04T22:04:48Z",
            status: "committed",
            note: "transfer",
          },
          {
            task: "t3",
            title: "Process",
            assignee: "Member A",
            start: "2031-06-05T00:57:36Z",
            end: "2031-06-05T15:21:36Z",
            status: "committed",
          },
          {
            task: "t4",
            title: "Return to Member B",
            assignee: "Member B",
            start: "2031-06-05T15:21:36Z",
            end: "2031-06-06T05:45:36Z",
            status: "committed",
          },
          {
            task: "t5",
            title: "Review resource",
            assignee: "Member B",
            start: "2031-06-06T07:12:00Z",
            end: "2031-06-07T00:28:48Z",
            status: "committed",
            note: "Fri",
          },
          {
            task: "t6",
            title: "Process model",
            assignee: "Member C",
            start: "2031-06-07T01:55:12Z",
            end: "2031-06-09T21:07:12Z",
            status: "committed",
            note: "weekend run · results Mon",
          },
        ],
        now: "2031-06-05T10:48:00Z",
        deadlines: [{ at: "2031-06-09T21:36:00Z", label: "Mon 12:00" }],
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
          { task: "t1", title: "prepare", status: "done" },
          {
            task: "t2",
            title: "transfer",
            status: "negotiating",
            change: "Member B moved t2 by one day",
          },
          { task: "t3", title: "process", status: "negotiating" },
          { task: "t4", title: "return", status: "negotiating" },
          { task: "t5", title: "review", status: "negotiating" },
          { task: "t7", title: "report draft", status: "negotiating" },
          { task: "t6", title: "model", status: "negotiating" },
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
          {
            text: "Receive resource",
            done: true,
            by: "self",
            evidence: "",
            task: { id: "t3", title: "Process" },
          },
          { text: "Record evidence", done: true, by: "self", evidence: "" },
          { text: "Ramp to 1 150 units", done: false, by: "self", evidence: "resource live" },
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
          { start: "Tue 3 · 17:20", title: "Task 1", assignee: "Member A", state: "done" },
          { start: "Wed 4 · 16:00", title: "Task 2", assignee: "Member B", state: "done" },
          { start: "Thu 5", title: "Task 3", assignee: "Member A", state: "now" },
          { start: "Fri 6 · 14:00", title: "Task 5", assignee: "Member B", state: "next" },
          { start: "Mon 9 · 12:00", title: "Model results", assignee: "Member C", state: "next" },
        ],
        now: "2030-06-05T12:00:00Z",
      },
    },
  ],
  ...planningExamples,
};
