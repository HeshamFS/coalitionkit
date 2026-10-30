// SPDX-License-Identifier: Apache-2.0

import type { Node } from "../../gallery/Drawn";
import { examples } from "./examples";
import { inviteIllustration, sheetData } from "./sheet-data";
import { list } from "./ui";

const text = (id: string, value: string, variant = "body"): Node => ({
  id,
  component: "Text",
  text: value,
  variant,
});
const row = (id: string, children: string[]): Node => ({
  id,
  component: "Row",
  children,
  gap: "8",
});
const subject = { kind: "plan", id: "p1", revision: { value: 2, event_ref: "example:44" } };

export const shellNodes: Node[] = [
  {
    id: "room-content",
    component: "Column",
    children: ["room-plan", "room-alternative", "room-task", "room-pending"],
    gap: "8",
  },
  {
    id: "room-plan",
    component: "Card",
    children: ["room-plan-head", "room-plan-body", "room-plan-badges"],
  },
  row("room-plan-head", ["room-plan-title", "room-plan-state"]),
  text("room-plan-title", "Plan A · work together"),
  { id: "room-plan-state", component: "Tag", kind: "needs", label: "Needs you" },
  text("room-plan-body", "07:10 start, 3 places · resource near P1 · task at 22:30", "caption"),
  row("room-plan-badges", ["room-model", "room-steward"]),
  { id: "room-model", component: "Badge", kind: "model", label: "Model output" },
  { id: "room-steward", component: "Badge", kind: "signed", label: "Steward passed" },
  {
    id: "room-alternative",
    component: "Card",
    children: ["room-alternative-head", "room-alternative-body"],
  },
  row("room-alternative-head", ["room-alternative-title", "room-alternative-state"]),
  text("room-alternative-title", "Plan B · split up"),
  { id: "room-alternative-state", component: "Badge", label: "Proposed", kind: "estimate" },
  text("room-alternative-body", "Two start 09:40, one waits for 07:10", "caption"),
  {
    id: "room-task",
    component: "Card",
    tone: "live",
    children: ["room-task-head", "room-task-body"],
  },
  row("room-task-head", ["room-task-title", "room-task-state"]),
  text("room-task-title", "Task at Place 1"),
  { id: "room-task-state", component: "Tag", kind: "changed", label: "Changed" },
  {
    id: "room-task-body",
    component: "Row",
    gap: "4",
    children: ["room-task-prefix", "room-task-time", "room-task-suffix"],
  },
  text("room-task-prefix", "starts", "caption"),
  { id: "room-task-time", component: "ChangedValue", after: "22:45" },
  text("room-task-suffix", "· 3 places · ≈ €14 each", "caption"),
  { id: "room-pending", component: "Card", tone: "dashed", children: ["room-pending-row"] },
  {
    id: "room-pending-row",
    component: "Row",
    gap: "4",
    align: "start",
    children: ["room-pending-spinner", "room-pending-text"],
  },
  { id: "room-pending-spinner", component: "Spinner", label: "Weighing a third plan" },
  text("room-pending-text", "Organizer is weighing a third plan…", "caption"),
  {
    id: "phone-content",
    component: "Column",
    children: ["phone-plan", "phone-task", "phone-offers"],
    gap: "8",
  },
  {
    id: "phone-plan",
    component: "Card",
    tone: "ask",
    children: ["phone-plan-head", "phone-plan-body", "phone-plan-actions"],
  },
  row("phone-plan-head", ["phone-plan-title", "phone-plan-deadline"]),
  text("phone-plan-title", "Decide: Plan A"),
  text("phone-plan-deadline", "18 min", "caption"),
  text("phone-plan-body", "Together on the 07:10, item near P1", "caption"),
  row("phone-plan-actions", ["phone-accept", "phone-decline"]),
  {
    id: "phone-accept",
    component: "Button",
    label: "Accept",
    size: "sm",
    variant: "primary",
    action: { name: "open", context: { subject } },
  },
  {
    id: "phone-decline",
    component: "Button",
    label: "Not this",
    size: "sm",
    action: { name: "open", context: { subject } },
  },
  { id: "phone-task", component: "Card", children: ["room-task-head", "phone-task-body"] },
  text("phone-task-body", "starts 22:45 · you, B, C", "caption"),
  { id: "phone-offers", component: "Card", children: ["phone-offers-head", "phone-offers-body"] },
  row("phone-offers-head", ["phone-offers-title", "phone-offers-count"]),
  text("phone-offers-title", "Your offers"),
  { id: "phone-offers-count", component: "Badge", kind: "estimate", label: "2" },
  text("phone-offers-body", "Resource 1 · Resource 2", "caption"),
];

function rootNode(name: string): Node {
  return {
    id: "root",
    component: name,
    ...examples[name],
    ...sheetData[name],
    ...(name === "RoomShell"
      ? {
          canvas: "room-content",
          deck: list(examples.RoomShell?.deck).map((item) => ({
            ...item,
            attention: item.id === "needs" || item.id === "consents",
          })),
        }
      : {}),
    ...(name === "PhoneShell" ? { stack: ["phone-content"] } : {}),
    ...(name === "InviteCard"
      ? {
          invitation: {
            title: "Working together in Group 1",
            url: "coalitionkit.dev/j/7Q4-M2X",
            qr: inviteIllustration,
          },
          expires: new Date(Date.now() + 23 * 3600000).toISOString(),
        }
      : {}),
    ...(name === "ConsentTray"
      ? {
          requests: [
            {
              kind: "plan",
              label: "Plan A · work together",
              deadline: "18 min",
              subject: {
                kind: "plan",
                id: "p1",
                revision: { value: 2, event_ref: "example:44" },
              },
            },
            {
              kind: "commitment",
              label: "Your commitment: book Resource 1",
              deadline: "today",
              subject: {
                kind: "commitment",
                id: "c1",
                revision: { value: 1, event_ref: "example:44" },
              },
            },
            {
              kind: "charter",
              label: "Revision 3: budget raised to €2",
              subject: {
                kind: "charter",
                id: "c2",
                revision: { value: 3, event_ref: "example:44" },
              },
            },
          ],
        }
      : {}),
  };
}

const supportingNodes: Node[] = [
  {
    id: "header",
    component: "TopBar",
    title: "Coalition 1",
    stage: { path: "/stage" },
    presence: examples.TopBar?.presence,
  },
  { id: "dock", component: "AgentDock", ...examples.AgentDock },
  {
    id: "tray",
    component: "ConsentTray",
    requests: [
      {
        label: "Plan A",
        deadline: "22:40",
        kind: "plan",
        subject: {
          kind: "plan",
          id: "p1",
          revision: { value: 2, event_ref: "example:44" },
        },
      },
    ],
  },
  ...shellNodes,
  {
    id: "detail-title",
    component: "Text",
    text: "Plan A · work together",
    variant: "body",
  },
  {
    id: "detail-fields",
    component: "KeyValue",
    pairs: [
      { label: "Ends", value: "09:05" },
      { label: "You pay", value: "≈ €96" },
      { label: "Load", value: "even" },
    ],
  },
  {
    id: "detail-actions",
    component: "Row",
    children: ["detail-accept", "detail-compare"],
    gap: "8",
  },
  {
    id: "detail-accept",
    component: "Button",
    label: "Accept",
    size: "sm",
    variant: "primary",
  },
  { id: "detail-compare", component: "Button", label: "Compare", size: "sm" },
];

export function sheetNodes(name: string): Node[] {
  return [rootNode(name), ...supportingNodes];
}
