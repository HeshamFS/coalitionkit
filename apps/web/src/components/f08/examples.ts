// SPDX-License-Identifier: Apache-2.0

import type { Props } from "../f08/shared";
import { stateProps } from "../f08/stateProps";
import { sheetData } from "./sheetData";

type Example = {
  name: string;
  props: string;
  events: string;
  states: { state: string; props: Props }[];
};
const drawn: Example[] = [
  {
    name: "ApprovalButton",
    props: "consequence, decision_deadline, disabledReason, label, subject",
    events: "approve → owner-signed",
    states: [
      {
        state: "ready",
        props: {
          label: "Approve",
          consequence: "Accept Task 3",
          subject: { kind: "plan", id: "Plan A", revision: { value: 2, event_ref: "example:1" } },
          decision_deadline: "2099-10-30T16:00:00Z",
        },
      },
      {
        state: "disabled",
        props: {
          label: "Approve",
          consequence: "Accept Task 3",
          subject: { kind: "plan", id: "Plan A", revision: { value: 2, event_ref: "example:1" } },
          decision_deadline: "2099-10-30T16:00:00Z",
          disabledReason: "Review the latest revision first",
        },
      },
    ],
  },
  {
    name: "CanaryMonitor",
    props: "canaries, found, runs, surfaces",
    events: "display only",
    states: [
      {
        state: "clean",
        props: {
          canaries: { value: 20, event_ref: "example:1" },
          runs: { value: 3, event_ref: "example:1" },
          found: { value: 0, event_ref: "example:1" },
          surfaces: ["log", "feed", "deltas", "A2UI", "traces"],
        },
      },
    ],
  },
  {
    name: "CommitmentCard",
    props: "assignee, commitment_id, decision_deadline, due, status, subject, task",
    events: "commit.approve, commit.withdraw",
    states: [
      {
        state: "pending",
        props: {
          task: "Task 3",
          assignee: "Member A",
          commitment_id: "c1",
          subject: { kind: "plan", id: "Plan A", revision: { value: 2, event_ref: "example:1" } },
          status: "pending",
          due: "Wed 17:00",
          decision_deadline: "2099-10-30T16:00:00Z",
        },
      },
      {
        state: "approved",
        props: {
          task: "Task 3",
          assignee: "Member A",
          commitment_id: "c1",
          subject: { kind: "plan", id: "Plan A", revision: { value: 2, event_ref: "example:1" } },
          status: "approved",
          due: "Wed 17:00",
          decision_deadline: "2099-10-30T16:00:00Z",
        },
      },
      {
        state: "suspended",
        props: {
          task: "Task 3",
          assignee: "Member A",
          commitment_id: "c1",
          subject: { kind: "plan", id: "Plan A", revision: { value: 2, event_ref: "example:1" } },
          status: "suspended",
          due: "Wed 17:00",
          decision_deadline: "2099-10-30T16:00:00Z",
        },
      },
      {
        state: "withdrawn",
        props: {
          task: "Task 3",
          assignee: "Member A",
          commitment_id: "c1",
          subject: { kind: "plan", id: "Plan A", revision: { value: 2, event_ref: "example:1" } },
          status: "withdrawn",
          due: "Wed 17:00",
          decision_deadline: "2099-10-30T16:00:00Z",
        },
      },
    ],
  },
  {
    name: "ConsentCard",
    props: "consequence, consequenceOfNo, cost, decision_deadline, subject, summary, yourPart",
    events: "decide(yes|no) owner-signed, compare",
    states: [
      {
        state: "open",
        props: {
          summary: "Finish Wednesday, results Monday",
          consequence: "Accept tasks t2, t4 and t5",
          yourPart: "t2, t4, t5 · 9 h",
          cost: "≈ €52.67 after split",
          consequenceOfNo: "Planner re-plans",
          subject: { kind: "plan", id: "Plan A", revision: { value: 2, event_ref: "example:1" } },
          decision_deadline: "2099-10-30T16:00:00Z",
        },
      },
      {
        state: "expired",
        props: {
          summary: "Finish Wednesday, results Monday",
          consequence: "Accept tasks t2, t4 and t5",
          yourPart: "t2, t4, t5 · 9 h",
          cost: "≈ €52.67 after split",
          consequenceOfNo: "Planner re-plans",
          subject: { kind: "plan", id: "Plan A", revision: { value: 2, event_ref: "example:1" } },
          decision_deadline: "2020-01-01T00:00:00Z",
        },
      },
    ],
  },
  {
    name: "DecisionLog",
    props: "entries",
    events: "entry.open",
    states: [
      {
        state: "default",
        props: {
          entries: [
            {
              time: "10:42",
              participant: "Member A",
              subject: "Plan A",
              revision: { value: 2, event_ref: "example:1" },
              answer: "yes",
              seq: { value: 41, event_ref: "example:1" },
              verified: true,
            },
          ],
        },
      },
    ],
  },
  {
    name: "DisclosureLadder",
    props: "buckets, field, level, overrides",
    events: "disclosure.raise → consent, disclosure.lower",
    states: [
      {
        state: "default",
        props: { field: "Usage limit", level: "bool", buckets: ['"€80 – €150"'], overrides: [] },
      },
    ],
  },
  {
    name: "DurableConsent",
    props: "grants, requests",
    events: "grant.allow, grant.revoke",
    states: [
      {
        state: "default",
        props: {
          grants: [
            {
              grantee: "Member A",
              action: "Read availability",
              scope: "task:t3",
              expires: "Friday",
              signed: true,
            },
          ],
          requests: [{ id: "r1", action: "Read result", grantee: "Member B" }],
        },
      },
    ],
  },
  {
    name: "OverlapView",
    props: "mode, parties, result, run, tokens",
    events: "display only",
    states: [
      {
        state: "running",
        props: {
          mode: "intersection",
          parties: ["Member A", "Member B", "Member C"],
          tokens: ["e3a1·77f0·c2…", "9b04·1de8·5a…", "41c9·b2e3·0f… ✓ match"],
          result: "slots",
          run: "r1",
        },
      },
    ],
  },
  {
    name: "PrivateField",
    props: "display, policy, reveal",
    events: "field.reveal",
    states: [
      {
        state: "masked",
        props: {
          display: "•••• ••••",
          policy: "vault",
          reveal: { value: 10, event_ref: "example:1" },
        },
      },
    ],
  },
  {
    name: "ProjectionNote",
    props: "removed, source, viewerSpecific",
    events: "projection.verify",
    states: [
      {
        state: "default",
        props: {
          removed: { value: 3, event_ref: "example:1" },
          viewerSpecific: true,
          source: {
            event_id: "e1",
            seq: { value: 40, event_ref: "example:1" },
            prev_hash: "a8c1…",
            hash: "8f2e…",
          },
        },
      },
    ],
  },
  {
    name: "RedactionDiff",
    props: "delivered, original, verdict",
    events: "redaction.appeal",
    states: [
      {
        state: "default",
        props: {
          original: "Task starts at four · private contact",
          delivered: "Task starts at four ▰▰▰",
          verdict: {
            action: "redact",
            policy_id: "no-contact-before-consent",
            paths: ["payload.text"],
          },
        },
      },
    ],
  },
  {
    name: "ScopeBadge",
    props: "audience, redact",
    events: "display only",
    states: [
      { state: "host", props: { audience: "host", redact: [] } },
      { state: "self", props: { audience: "self", redact: [] } },
      { state: "task:t3", props: { audience: "task:t3", redact: [] } },
      { state: "role:member", props: { audience: "role:member", redact: [] } },
      { state: "coalition", props: { audience: "coalition", redact: [] } },
      { state: "public", props: { audience: "public", redact: [] } },
      { state: "redacted", props: { audience: "coalition", redact: ["payload.cost"] } },
    ],
  },
  {
    name: "StaleNotice",
    props: "currentRevision, decision_deadline, diff, subject, yourRevision",
    events: "subject.review",
    states: [
      {
        state: "shown",
        props: {
          subject: { kind: "plan", id: "Plan A", revision: { value: 2, event_ref: "example:1" } },
          yourRevision: { value: 2, event_ref: "example:1" },
          currentRevision: { value: 3, event_ref: "example:1" },
          diff: ["− t2 Wed 16:00", "+ t2 Wed 17:00"],
          decision_deadline: "2099-10-30T16:00:00Z",
        },
      },
    ],
  },
  {
    name: "VaultCard",
    props: "answersToday, categories, location",
    events: "vault.export, vault.wipe",
    states: [
      {
        state: "default",
        props: {
          location: "device",
          answersToday: { value: 7, event_ref: "example:1" },
          categories: [
            { name: "Limits", count: { value: 3, event_ref: "example:1" }, policy: "answer-only" },
            { name: "Calendar", count: { value: 142, event_ref: "example:1" }, policy: "psi" },
            { name: "Documents", count: { value: 2, event_ref: "example:1" }, policy: "masked" },
            { name: "Transcripts", count: { value: 1, event_ref: "example:1" }, policy: "never" },
          ],
        },
      },
    ],
  },
  {
    name: "VoteTally",
    props: "answered, answers, deciders, decision_deadline, outcome, rule, subject",
    events: "display only",
    states: [
      {
        state: "open",
        props: {
          subject: { kind: "plan", id: "Plan A", revision: { value: 2, event_ref: "example:1" } },
          answered: { value: 1, event_ref: "example:1" },
          deciders: ["Member A", "Member B", "Member C"],
          rule: "every member",
          decision_deadline: "2099-10-30T16:00:00Z",
        },
      },
      {
        state: "closed",
        props: {
          subject: { kind: "plan", id: "Plan A", revision: { value: 2, event_ref: "example:1" } },
          answered: { value: 1, event_ref: "example:1" },
          deciders: ["Member A", "Member B", "Member C"],
          rule: "every member",
          decision_deadline: "2099-10-30T16:00:00Z",
          outcome: "split",
          answers: [
            { participant: "Member A", answer: true },
            { participant: "Member B", answer: true },
            { participant: "Member C", answer: false },
          ],
        },
      },
    ],
  },
  {
    name: "WhatOthersKnow",
    props: "rows",
    events: "view.export",
    states: [
      {
        state: "default",
        props: {
          rows: [
            {
              participant: "Member B",
              knows: ["free Thu 09:00", "offer of Resource 1"],
              notKnows: ["other slots", "budget"],
              because: "task:t3 · PSI",
            },
            {
              participant: "Host",
              knows: ["signed messages"],
              notKnows: ["your vault"],
              because: "it keeps the log",
            },
          ],
        },
      },
    ],
  },
];

const states: Record<string, string[]> = {
  ApprovalButton: ["ready", "disabled", "signing"],
  CanaryMonitor: ["clean", "leak"],
  CommitmentCard: ["pending", "approved", "suspended", "withdrawn"],
  ConsentCard: ["open", "answered", "stale", "expired"],
  DecisionLog: ["default"],
  DisclosureLadder: ["default"],
  DurableConsent: ["default"],
  OverlapView: ["running", "done"],
  PrivateField: ["masked", "revealed"],
  ProjectionNote: ["default"],
  RedactionDiff: ["default"],
  ScopeBadge: ["default"],
  StaleNotice: ["shown"],
  VaultCard: ["default"],
  VoteTally: ["open", "closed"],
  WhatOthersKnow: ["default"],
};

export const examples: Example[] = drawn
  .map((example) => ({
    ...example,
    states: [
      ...example.states,
      ...(states[example.name] ?? [])
        .filter((state) => !example.states.some((s) => s.state === state))
        .map((state) => ({ state, props: { ...example.states[0]?.props } })),
    ],
  }))
  .map((example) => ({
    ...example,
    states: example.states.map((s) => ({
      ...s,
      props: sheetData(example.name, s.state, stateProps(example.name, s.state, s.props)),
    })),
  }));
