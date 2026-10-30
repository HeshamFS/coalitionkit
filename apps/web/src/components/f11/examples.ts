// SPDX-License-Identifier: Apache-2.0

import type { Props } from "../f08/shared";
import { stateProps } from "../f08/stateProps";

type Example = {
  name: string;
  props: string;
  events: string;
  states: { state: string; props: Props }[];
};
const drawn: Example[] = [
  {
    name: "ChannelHandoff",
    props: "from, reason, subject, to",
    events: "handoff.open",
    states: [
      {
        state: "offered",
        props: {
          summary: "resource ≈ €42",
          actionLabel: "buy the resource",
          from: "lens",
          to: "phone",
          reason: "money",
          subject: { kind: "plan", id: "Plan A", revision: { value: 2, event_ref: "example:1" } },
        },
      },
    ],
  },
  {
    name: "ChannelSettings",
    props: "channels, overrides, quiet",
    events: "channel.set(kind, level), quiet.set",
    states: [
      {
        state: "default",
        props: {
          channels: [
            { kind: "Push", label: "Web and phone app", level: "everything" },
            { kind: "Message", label: "WhatsApp", level: "needs-you" },
            { kind: "Lens", label: "Glasses", level: "next-step" },
            {
              kind: "Email",
              label: "Email digest",
              level: "off",
              offLabel: "daily 08:00",
              enabledLevel: "digest",
            },
          ],
          quiet: { from: "22:00", to: "07:00", tz: "Europe/Berlin" },
          overrides: [],
        },
      },
    ],
  },
  {
    name: "CoalitionArchive",
    props: "items",
    events: "archive.open(id)",
    states: [
      {
        state: "default",
        props: {
          items: [
            {
              coalition: "Coalition 1",
              pack: "Coordination",
              ended: "2026-11-09T12:40:00Z",
              outcome: "reached",
              yourCost: "€0.24",
              log: "log:1",
            },
            {
              coalition: "Coalition 2",
              pack: "Planning",
              ended: "2026-10-29T12:40:00Z",
              outcome: "reached",
              yourCost: "€0.12",
              log: "log:2",
            },
            {
              coalition: "Coalition 3",
              pack: "none",
              ended: "Sep",
              outcome: "partly",
              yourCost: "€0.05",
              log: "log:3",
            },
          ],
        },
      },
      { state: "empty", props: { items: [] } },
    ],
  },
  {
    name: "CostMeter",
    props: "budget, rows, total",
    events: "display only",
    states: [
      {
        state: "ok",
        props: {
          budget: { value: 3, event_ref: "example:1" },
          total: { value: 0.71, event_ref: "example:1" },
          rows: [
            {
              role: "Gardener",
              model: "Muse Wonder",
              cost: { value: 0.38, event_ref: "example:1" },
            },
            { role: "Members", model: "Muse Spark", cost: { value: 0.19, event_ref: "example:1" } },
            { role: "Steward", model: "Spark Open", cost: { value: 0.09, event_ref: "example:1" } },
            {
              role: "Mint",
              model: "Wonder + Spark",
              cost: { value: 0.05, event_ref: "example:1" },
            },
          ],
        },
      },
      {
        state: "warning 80%",
        props: {
          budget: { value: 1, event_ref: "example:1" },
          total: { value: 0.8, event_ref: "example:1" },
          rows: [
            {
              role: "Planner",
              model: "Model A",
              tokens: { value: 12400, event_ref: "example:1" },
              cost: { value: 0.24, event_ref: "example:1" },
            },
            {
              role: "Steward",
              model: "Model B",
              tokens: { value: 3200, event_ref: "example:1" },
              cost: { value: 0.11, event_ref: "example:1" },
            },
          ],
        },
      },
      {
        state: "stopped 100%",
        props: {
          budget: { value: 1, event_ref: "example:1" },
          total: { value: 1, event_ref: "example:1" },
          rows: [
            {
              role: "Planner",
              model: "Model A",
              tokens: { value: 12400, event_ref: "example:1" },
              cost: { value: 0.24, event_ref: "example:1" },
            },
            {
              role: "Steward",
              model: "Model B",
              tokens: { value: 3200, event_ref: "example:1" },
              cost: { value: 0.11, event_ref: "example:1" },
            },
          ],
        },
      },
    ],
  },
  {
    name: "DissolveSummary",
    props: "contributions, cost, counts, goal, log, outcome",
    events: "log.download, results.open",
    states: [
      {
        state: "default",
        props: {
          goal: "The three-member project reached its goal",
          outcome: "reached",
          counts: {
            tasks: { value: 6, event_ref: "example:1" },
            total: { value: 6, event_ref: "example:1" },
            ended: "Dissolved · Mon 9 Nov 12:40",
            summary:
              "Resource prepared, transferred, reviewed and processed; results shared Monday 11:52.",
            decisions: { value: 4, event_ref: "example:1" },
            replans: { value: 1, event_ref: "example:1" },
          },
          contributions: [
            {
              participant: "Member A",
              tasks: "prepare, process",
              hours: { value: 14, event_ref: "example:1" },
            },
            {
              participant: "Member B",
              tasks: "transfer both ways, review",
              hours: { value: 9, event_ref: "example:1" },
            },
            {
              participant: "Member C",
              tasks: "process results",
              hours: { value: 11, event_ref: "example:1" },
            },
          ],
          cost: "€0.71",
          log: "sealed:88",
        },
      },
    ],
  },
  {
    name: "DoorMatrix",
    props: "doors, target",
    events: "display only",
    states: [
      {
        state: "default",
        props: {
          target: "ConsentCard",
          doors: [
            {
              kind: "wide",
              title: "Decide · Plan A",
              body: "Start Wed, results Mon · your part t2, t4, t5",
            },
            { kind: "compact", title: "Decide · Plan A", body: "Results Mon · 2 h left" },
            {
              kind: "message",
              body: "Plan A: start Wed, results Mon. Your part: both transfers and the review.",
              deadline: "decide by 14:00",
            },
            {
              kind: "voice",
              body: '"Plan A starts Wednesday and gets results Monday. Say accept, no, or tell me more."',
              confirm: 'confirm: "Accept Plan A. Signing."',
            },
            {
              kind: "lens",
              title: "Plan A: results Monday",
              body: "Pinch to accept on your phone",
              deadline: "DECIDE · 2 H",
            },
            { kind: "mcp-app", title: "Accept Plan A, revision 2?" },
          ],
        },
      },
    ],
  },
  {
    name: "ExportControl",
    props: "items",
    events: "export.zip, vault.wipe",
    states: [
      {
        state: "default",
        props: {
          items: [
            { kind: "Sealed log (your projection) + receipts", size: "42 KB", included: true },
            { kind: "Your vault answers", size: "8 KB", included: true },
            { kind: "Call transcripts (yours only)", size: "12 KB", included: false },
          ],
        },
      },
    ],
  },
  {
    name: "LessonReview",
    props: "lessons",
    events: "lessons.save",
    states: [
      {
        state: "suggested",
        props: {
          lessons: [
            {
              text: "Use the express option when results are needed within 5 days.",
              from: ["tension t-2 · you chose speed over €66"],
              scope: "private",
              kind: "timing",
            },
            {
              text: "Resource 3 is free on weekends; ask before Friday.",
              from: ["scheduling · Member C agreed to share this"],
              scope: "shareable",
              kind: "coordination",
            },
            {
              text: "Member B is slow to answer queries.",
              from: [],
              scope: "private",
              kind: "judgement",
            },
          ],
        },
      },
    ],
  },
  {
    name: "MessageTemplate",
    props: "params, quickReplies, template",
    events: "reply(id)",
    states: [
      {
        state: "sent",
        props: {
          template: "decision_needed · v3",
          params: ["Coalition 1", "A decision needs you: Plan A, by 14:00 today."],
          quickReplies: { value: 3, event_ref: "example:1" },
        },
      },
    ],
  },
  {
    name: "MetricTile",
    props: "context, label, run, unit, value",
    events: "display only",
    states: [
      {
        state: "measured",
        props: {
          label: "Replan latency",
          value: { value: 4.2, event_ref: "example:1" },
          unit: "s",
          context: "p95 · last run",
          run: "run:1",
        },
      },
      {
        state: "not run yet",
        props: { label: "Replan latency", unit: "s", context: "p95 · last run", run: "run:1" },
      },
    ],
  },
  {
    name: "NotificationCard",
    props: "body, link, title",
    events: "notification.open",
    states: [
      {
        state: "delivered",
        props: {
          title: "Coalition 1",
          body: "Plan A needs your answer. Open to review.",
          link: "/room/1",
        },
      },
    ],
  },
  {
    name: "Scorecard",
    props: "tiles",
    events: "display only",
    states: [
      {
        state: "default",
        props: {
          tiles: [
            {
              label: "privacy leaks",
              value: { value: 0, event_ref: "example:1" },
              context: "[RUNS] runs",
            },
            {
              label: "lost events",
              value: { value: 0, event_ref: "example:1" },
              context: "3 208 events",
            },
            { label: "change to paint p95", placeholder: "[MS]", context: "target < 1 s" },
            {
              label: "ripple p95",
              value: { value: 64, event_ref: "example:1" },
              unit: "ms",
              context: "20 tasks",
            },
          ],
        },
      },
    ],
  },
  {
    name: "SkillCard",
    props: "name, roles, rules, source, templates",
    events: "coalition.create(from skill)",
    states: [
      {
        state: "draft",
        props: {
          name: "Three-member task run",
          usedCount: { value: 1, event_ref: "example:1" },
          summary:
            "Make → send → run → check → model, with the transfer rule and a 4-hour decision window.",
          source: "Coalition 1",
          roles: ["Coordinator", "Member", "Reviewer"],
          rules: [
            "with the transfer rule and a 4-hour decision window",
            "Every member approves",
            "Private values stay local",
            "Review results",
          ],
          templates: ["Prepare", "transfer", "process", "review", "model", "share"],
        },
      },
    ],
  },
];

const states: Record<string, string[]> = {
  ChannelHandoff: ["offered", "opened", "expired"],
  ChannelSettings: ["default"],
  CoalitionArchive: ["default", "empty"],
  CostMeter: ["ok", "warning 80%", "stopped 100%"],
  DissolveSummary: ["default"],
  DoorMatrix: ["default"],
  ExportControl: ["default", "exporting", "wiped"],
  LessonReview: ["suggested", "saved"],
  MessageTemplate: ["sent", "replied"],
  MetricTile: ["measured", "not run yet"],
  NotificationCard: ["delivered", "grouped"],
  Scorecard: ["default"],
  SkillCard: ["draft", "shared"],
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
      props: stateProps(example.name, s.state, s.props),
    })),
  }));
