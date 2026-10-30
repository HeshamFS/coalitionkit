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
            { kind: "Push", level: "needs-you" },
            { kind: "Message", level: "next-step" },
            { kind: "Email", level: "everything" },
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
              pack: "Core",
              ended: "Oct 28",
              outcome: "reached",
              yourCost: "€52.67",
              log: "log:1",
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
          budget: { value: 1, event_ref: "example:1" },
          total: { value: 0.35, event_ref: "example:1" },
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
          goal: "Task 3 completed",
          outcome: "reached",
          counts: {
            tasks: { value: 8, event_ref: "example:1" },
            decisions: { value: 3, event_ref: "example:1" },
            replans: { value: 2, event_ref: "example:1" },
          },
          contributions: [
            {
              participant: "Member A",
              tasks: { value: 3, event_ref: "example:1" },
              hours: { value: 9, event_ref: "example:1" },
            },
            {
              participant: "Member B",
              tasks: { value: 5, event_ref: "example:1" },
              hours: { value: 12, event_ref: "example:1" },
            },
          ],
          cost: "€158 total · €52.67 each",
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
          doors: ["wide", "compact", "message", "voice", "lens", "mcp-app"],
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
            { kind: "Signed log", size: "42 KB", included: true },
            { kind: "Receipts", size: "8 KB", included: true },
            { kind: "Private vault", size: "12 KB", included: false },
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
            { text: "Allow extra time for Task 3", from: ["t3"], scope: "private", kind: "timing" },
            {
              text: "Check availability first",
              from: ["t2"],
              scope: "shareable",
              kind: "coordination",
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
          template: "decision.request · v1",
          params: ["Coalition 1", "Plan A needs your answer"],
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
              label: "Replan latency",
              value: { value: 4.2, event_ref: "example:1" },
              unit: "s",
              context: "p95",
              run: "run:1",
            },
            {
              label: "Privacy leaks",
              value: { value: 0, event_ref: "example:1" },
              unit: "",
              context: "3 runs",
              run: "run:2",
            },
            { label: "Recovery time", unit: "s" },
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
          name: "Shared task coordination",
          source: "Coalition 1",
          roles: ["Coordinator", "Member", "Reviewer"],
          rules: ["Every member approves", "Private values stay local"],
          templates: ["Plan", "Task", "Decision"],
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
