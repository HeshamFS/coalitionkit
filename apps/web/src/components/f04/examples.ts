// SPDX-License-Identifier: Apache-2.0
import type { Data } from "../f02/ui";
export const examples: Record<string, Data> = {
  AcceptanceForm: {
    charter: "c1",
    subject: { kind: "charter", id: "p1", revision: { value: 3, event_ref: "example:44" } },
    consequence: "Until you accept, your open commitments are paused and new offers don't count.",
    diff: [
      {
        rule: "Agent budget",
        heading: "The budget rule changed",
        before: "€1 for the coalition",
        after: "€2 for the coalition",
      },
    ],
    decision_deadline: "2099-11-01T12:00:00Z",
  },
  AvailabilityGrid: {
    days: ["Mon", "Tue", "Wed", "Thu", "Fri"],
    slots: ["09:00", "11:00", "13:00", "15:00", "17:00"].flatMap((time, row) =>
      ["Mon", "Tue", "Wed", "Thu", "Fri"].map((day, column) => ({
        id: `${day}${time}`,
        day,
        label: time,
        available: ["11010", "10011", "00111", "11100", "01001"][row]?.[column] === "1",
      })),
    ),
    source: "manual",
  },
  ConsentSeal: {
    subject: { kind: "plan", id: "p1", revision: { value: 2, event_ref: "example:44" } },
    summary: "Buy the resource for three · ≈ €42\nB and C pay you back through the coalition log.",
    holdMs: { value: 1200, event_ref: "example:44" },
    decision_deadline: "2099-11-01T12:00:00Z",
  },
  DocumentShare: {
    document: "document:1",
    purpose: "Share only what proves the cancellation.",
    preview: {
      title: "RESOURCE PASS",
      rows: [
        { field: "Owner" },
        { field: "Task", value: "482 · CANCELLED" },
        { field: "Reference" },
        { field: "Position", value: "14C" },
      ],
    },
    masks: [
      { field: "Owner", by: "agent" },
      { field: "Reference", by: "agent" },
    ],
  },
  FeedbackForm: {
    audience: "me",
    questions: [
      {
        id: "q1",
        label: "Did the coalition reach its goal?",
        kind: "choice",
        options: [
          { id: "no", label: "No" },
          { id: "partly", label: "Partly" },
          { id: "yes", label: "Yes" },
        ],
      },
      { id: "q2", label: "Was the load fair?", kind: "scale" },
      { id: "q3", label: "One lesson for next time", kind: "text" },
    ],
  },
  Form: {
    title: "Your part of the task",
    description: "Planner asks so it can plan. Fields marked private never leave your vault.",
    show_schema: true,
    scope: "task:t2",
    submit_label: "Send to Planner",
    fields: [
      { id: "finish_by", label: "Finish by", kind: "datetime", display_label: "Tomorrow 10:00" },
      {
        id: "max_cost",
        label: "Most you'll pay for the resource",
        kind: "money",
        private: "answer-only",
        display_value: { value: 140, event_ref: "example:44" },
        unit: "per use",
        help: 'Agents only learn "within" or "over"',
      },
      {
        id: "items",
        label: "Items",
        kind: "choice",
        initial: "small",
        options: [
          { id: "none", label: "None" },
          { id: "small", label: "Small" },
          { id: "large", label: "Large" },
        ],
      },
      { id: "share_slot", label: "Happy to share a slot", kind: "bool" },
    ],
    submit_event: "coalition.offer",
  },
  LimitField: {
    shared_values: { time: "10:00" },
    limits: [
      { id: "cost", label: "Resource per use", disclose: "answer-only" },
      { id: "time", label: "Latest finish", disclose: "shared" },
      { id: "distance", label: "Distance at most", disclose: "answer-only" },
    ],
    queries: [
      {
        question: '"Is €96 within your resource limit?"',
        answer: "within",
        asker: "Agent B",
        time: "22:15",
      },
      { question: '"Is €160 within…?"', answer: "over", asker: "Agent B", time: "22:16" },
    ],
  },
  NeedForm: {
    text: "A resource near the workspace",
    audience: "coalition",
    quantity: { value: 2, event_ref: "example:44" },
    constraints: [{ kind: "deadline", value: "01:00" }],
  },
  OfferForm: {
    what: "Twin slot, resource near workspace 1",
    target_label: "Slot before 01:00 · B",
    scope: "task:t2",
    target: "need",
    cost: { amount: { value: 118, event_ref: "example:44" }, kind: "estimate" },
    conditions: ["until 01:00", "quiet use"],
    expires: "2099-11-01T12:00:00Z",
  },
  OwnerSign: {
    subject_label: "Plan A",
    answer_label: "Yes",
    device_label: "this phone",
    subject: { kind: "plan", id: "p1", revision: { value: 2, event_ref: "example:44" } },
    answer: "bool",
    kid: "owner · 3b9e…71f",
    method: "passkey",
    decision_deadline: "2099-11-01T12:00:00Z",
  },
  Receipt: {
    subject: { kind: "plan", id: "p1", revision: { value: 2, event_ref: "example:44" } },
    seq: { value: 44, event_ref: "example:44" },
    receipt: { algorithm: "host ed25519", verified: true },
    hash: "5d0a…e19",
    remaining: ["C (1 of 3 left)"],
    decision_deadline: "2099-11-01T12:00:00Z",
  },
  ReviewStep: {
    notice:
      "Once published, the charter can only change by a new revision that every member accepts.",
    precheck: { passed: true },
    sections: [
      { label: "Goal", summary: "Finish by 10:00, together if possible", editStep: "goal" },
      { label: "Decisions", summary: "Every member · 30 minutes", editStep: "decisions" },
      { label: "Budget", summary: "€2 for agents for the whole coalition", editStep: "budget" },
    ],
  },
  ValidationSummary: {
    errors: [
      { field: "goal", text: "Add a goal" },
      { field: "date", text: "Choose a date in the future" },
    ],
  },
  Wizard: {
    current: "rules",
    canSkip: false,
    draft: { agreement: "all", deadline: "30" },
    steps: [
      {
        id: "goal",
        label: "Goal",
        fields: [{ id: "goal", label: "What do you want to do together?", kind: "text" }],
      },
      { id: "roles", label: "Roles" },
      {
        id: "rules",
        label: "Rules",
        prompt: "How should decisions work?",
        fields: [
          {
            id: "agreement",
            label: "Agreement",
            kind: "choice",
            options: [
              {
                id: "all",
                label: "Every member agrees",
                description: "Slower, but nobody is outvoted",
              },
              { id: "two", label: "Two of three", description: "The third can still leave" },
              {
                id: "organizer",
                label: "The organizer decides",
                description: "Others can only offer",
              },
            ],
          },
          {
            id: "deadline",
            label: "Time to decide",
            kind: "choice",
            options: [
              { id: "30", label: "30 minutes" },
              { id: "60", label: "60 minutes" },
            ],
          },
        ],
        suggestion: {
          emphasis: "every member agrees",
          text: "For a group of members in a workspace, every member agrees with a short deadline usually works. You can change it later with a new revision.",
        },
        summary: [
          { label: "Goal: finish by 10:00, together if not dearer" },
          { label: "Roles: organizer ×1, member ×2-5" },
          { label: "Rules: every member · 30 min", current: true },
        ],
      },
      { id: "budget", label: "Budget" },
      { id: "review", label: "Review" },
    ],
  },
};
export const groups = [
  ["Forms an agent generates", ["Form", "ValidationSummary"]],
  ["Step-by-step flows", ["Wizard", "NeedForm", "OfferForm"]],
  [
    "Private input: availability, limits, documents",
    ["AvailabilityGrid", "LimitField", "DocumentShare"],
  ],
  [
    "Acceptance: the moments that end in a signature",
    ["AcceptanceForm", "ConsentSeal", "OwnerSign", "Receipt", "ReviewStep", "FeedbackForm"],
  ],
];
export const labels: Record<string, { props: string; events: string }> = {
  AcceptanceForm: {
    props: "charter \u00b7 consequence \u00b7 decision_deadline \u00b7 diff \u00b7 subject",
    events: "decide(charter) owner-signed \u00b7 leave",
  },
  AvailabilityGrid: {
    props: "days \u00b7 slots \u00b7 source",
    events: "availability.paint \u00b7 availability.import",
  },
  ConsentSeal: {
    props: "decision_deadline \u00b7 holdMs \u00b7 subject \u00b7 summary",
    events: "decide | commit (owner-signed)",
  },
  DocumentShare: { props: "document \u00b7 masks \u00b7 purpose", events: "evidence.share(masks)" },
  FeedbackForm: { props: "audience \u00b7 questions", events: "feedback.save" },
  Form: { props: "fields \u00b7 submit_event \u00b7 title", events: "form.submit(values)" },
  LimitField: { props: "limits \u00b7 queries", events: "limit.change" },
  NeedForm: {
    props: "audience \u00b7 constraints \u00b7 quantity \u00b7 text",
    events: "coalition.need",
  },
  OfferForm: {
    props: "conditions \u00b7 cost \u00b7 expires \u00b7 target \u00b7 what",
    events: "coalition.offer",
  },
  OwnerSign: {
    props: "answer \u00b7 decision_deadline \u00b7 kid \u00b7 method \u00b7 subject",
    events: "sign.confirm",
  },
  Receipt: {
    props:
      "decision_deadline \u00b7 hash \u00b7 receipt \u00b7 remaining \u00b7 seq \u00b7 subject",
    events: "receipt.verify \u00b7 decide.change",
  },
  ReviewStep: { props: "notice \u00b7 precheck \u00b7 sections", events: "wizard.finish" },
  ValidationSummary: { props: "errors", events: "field.focus(id)" },
  Wizard: {
    props: "canSkip \u00b7 current \u00b7 draft \u00b7 steps",
    events: "wizard.next \u00b7 wizard.back \u00b7 wizard.finish",
  },
};
