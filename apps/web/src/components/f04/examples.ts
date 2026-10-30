// SPDX-License-Identifier: Apache-2.0
import type { Data } from "../f02/ui";
export const examples: Record<string, Data> = {
  AcceptanceForm: {
    charter: "c1",
    subject: { kind: "charter", id: "p1", revision: { value: 2, event_ref: "example:44" } },
    consequence: "Until you accept, open commitments are paused and new offers do not count.",
    diff: [{ rule: "Agent budget", before: "€1 for the coalition", after: "€2 for the coalition" }],
    decision_deadline: "2099-11-01T12:00:00Z",
  },
  AvailabilityGrid: {
    days: ["Mon", "Tue", "Wed", "Thu", "Fri"],
    slots: [
      { id: "Mon09:00", day: "Mon", label: "09:00", available: false },
      { id: "Mon10:00", day: "Mon", label: "10:00", available: false },
      { id: "Mon11:00", day: "Mon", label: "11:00", available: false },
      { id: "Tue09:00", day: "Tue", label: "09:00", available: true },
      { id: "Tue10:00", day: "Tue", label: "10:00", available: true },
      { id: "Tue11:00", day: "Tue", label: "11:00", available: true },
      { id: "Wed09:00", day: "Wed", label: "09:00", available: false },
      { id: "Wed10:00", day: "Wed", label: "10:00", available: false },
      { id: "Wed11:00", day: "Wed", label: "11:00", available: false },
      { id: "Thu09:00", day: "Thu", label: "09:00", available: false },
      { id: "Thu10:00", day: "Thu", label: "10:00", available: false },
      { id: "Thu11:00", day: "Thu", label: "11:00", available: false },
      { id: "Fri09:00", day: "Fri", label: "09:00", available: false },
      { id: "Fri10:00", day: "Fri", label: "10:00", available: false },
      { id: "Fri11:00", day: "Fri", label: "11:00", available: false },
    ],
    source: "manual",
  },
  ConsentSeal: {
    subject: { kind: "plan", id: "p1", revision: { value: 2, event_ref: "example:44" } },
    summary: "Provide Resource 1 for three · ≈ €42",
    holdMs: { value: 1200, event_ref: "example:44" },
    decision_deadline: "2099-11-01T12:00:00Z",
  },
  DocumentShare: {
    document: "document:1",
    purpose: "Share only what proves the change.",
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
    title: "Tell us what you need",
    fields: [
      { id: "goal", label: "Goal", kind: "text", required: true, help: "What should happen?" },
      { id: "date", label: "By when?", kind: "datetime" },
      {
        id: "limit",
        label: "Budget limit",
        kind: "money",
        private: "vault",
        help: "Only your agent can read this.",
      },
    ],
    submit_event: "form.submit",
  },
  LimitField: {
    limits: [{ id: "budget", label: "Budget limit", disclose: "answer-only" }],
    queries: [
      { question: "Does Plan A fit your limit?", answer: "Yes", asker: "Agent B", time: "22:15" },
    ],
  },
  NeedForm: {
    text: "Resource 1 by Friday",
    audience: "coalition",
    quantity: { value: 1, event_ref: "example:44" },
    constraints: [{ kind: "deadline", label: "Friday 16:00" }],
  },
  OfferForm: {
    what: "I can provide Resource 1",
    target: "need",
    cost: { amount: { value: 42, event_ref: "example:44" }, kind: "estimate" },
    conditions: ["After approval"],
    expires: "2099-11-01T12:00:00Z",
  },
  OwnerSign: {
    subject: { kind: "plan", id: "p1", revision: { value: 2, event_ref: "example:44" } },
    answer: "bool",
    kid: "owner · 3b9e…71f",
    method: "passkey",
    decision_deadline: "2099-11-01T12:00:00Z",
  },
  Receipt: {
    subject: { kind: "plan", id: "p1", revision: { value: 2, event_ref: "example:44" } },
    seq: { value: 44, event_ref: "example:44" },
    receipt: { algorithm: "host ed25519" },
    hash: "5d0a…e19",
    remaining: ["Member C"],
    decision_deadline: "2099-11-01T12:00:00Z",
  },
  ReviewStep: {
    notice: "After publishing, the charter can only change by a new revision every member accepts.",
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
    current: "goal",
    canSkip: false,
    draft: {},
    steps: [
      {
        id: "goal",
        label: "Goal",
        fields: [{ id: "goal", label: "What do you want to do together?", kind: "text" }],
      },
      { id: "members", label: "Members" },
      { id: "rules", label: "Rules" },
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
