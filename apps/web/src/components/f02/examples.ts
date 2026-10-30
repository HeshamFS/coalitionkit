// SPDX-License-Identifier: Apache-2.0
import type { Data } from "../f02/ui";
export const examples: Record<string, Data> = {
  AccountMenu: {
    identity: { label: "Member A", kid: "owner:1" },
    agents: [{ id: "a1", label: "Your agent" }],
    channels: [{ id: "web", label: "Web connected" }],
    appearance: "system",
  },
  AgentDock: {
    agent: "a1",
    composer: "text",
    messages: [
      {
        text: "Two plans passed the steward. A keeps the three of you together; B is cheaper but splits you up.",
      },
      { role: "user", text: "Which one finishes before 10?" },
      { text: "Both do. A ends 09:05, B 09:40. Your vault said yes to the resource price in A." },
      { role: "tool", text: "vault.answer(q7) → yes" },
    ],
  },
  BoardTemplate: {
    columns: ["open", "proposed", "done"],
    cards: [
      { id: "t1", title: "Task 1", status: "open" },
      { id: "t2", title: "Task 2", status: "proposed" },
      { id: "t3", title: "Task 3", status: "done" },
    ],
  },
  ConsentTray: {
    requests: [
      {
        kind: "plan",
        subject: { kind: "plan", id: "p1", revision: { value: 2, event_ref: "example:44" } },
        label: "Plan A",
      },
    ],
  },
  Deck: {
    selected: "now",
    sections: [
      { id: "now", label: "Now", count: { value: 2, event_ref: "example:44" } },
      { id: "plans", label: "Plans", count: { value: 2, event_ref: "example:44" } },
      { id: "people", label: "People", count: { value: 3, event_ref: "example:44" } },
    ],
  },
  EntryComposer: { goal: "text", packs: ["General"], attachments: [] },
  InviteCard: {
    invitation: { id: "invite:1", url: "coalitionkit.example/join/example" },
    role: "Member",
    channels: "link · QR",
    expires: "2099-11-01T12:00:00Z",
  },
  JoinScreen: {
    inviter: "Member A",
    charter: {
      summary: "Complete the shared goal together.",
      rules: [
        "Every member decides",
        "Private limits stay in your vault",
        "Changes need a new revision",
      ],
    },
    subject: { kind: "charter", id: "p1", revision: { value: 2, event_ref: "example:44" } },
  },
  LensCard: {
    eyebrow: "TASK 1 · 1 OF 1",
    title: "Task starts 22:45 at Place 3",
    body: "Walk 6 min · Members B and C are there",
    gestures: { value: 1, event_ref: "example:44" },
  },
  MessageDoor: {
    text: "Two plans ready by 10:00. Plan 1: together, about €96. Plan 2: separate, about €71. Decide by 22:40.",
    choices: [
      { n: { value: 1, event_ref: "example:44" }, label: "Plan 1", value: "p1" },
      { n: { value: 2, event_ref: "example:44" }, label: "Plan 2", value: "p2" },
    ],
    receipt: "coalitionkit.example/l/44",
  },
  NotificationCenter: {
    items: [
      { kind: "decision", text: "Plan A needs your answer", ref: "p1", time: "now", read: false },
      { kind: "changed", text: "Task 3 moved to Friday", ref: "t3", time: "2 min", read: false },
    ],
  },
  PageHeader: {
    title: "Plans",
    eyebrow: "COALITION 1",
    crumbs: ["Coalitions", "Coalition 1"],
    tabs: ["Compare", "History"],
    actions: { value: 2, event_ref: "example:44" },
  },
  PhoneShell: { tabs: "Now|Plans|People|Agent", header: "header", stack: ["content"] },
  RoomShell: {
    coalition: "Coalition 1",
    deck: [
      { id: "canvas", label: "Canvas", group: "This coalition" },
      {
        id: "charter",
        label: "Charter",
        prefix: "r",
        count: { value: 3, event_ref: "example:44" },
      },
      { id: "people", label: "People", count: { value: 3, event_ref: "example:44" } },
      { id: "needs", label: "Needs", count: { value: 2, event_ref: "example:44" } },
      { id: "offers", label: "Offers", count: { value: 7, event_ref: "example:44" } },
      { id: "plans", label: "Plans", count: { value: 2, event_ref: "example:44" } },
      { id: "tasks", label: "Tasks" },
      { id: "log", label: "Log", count: { value: 42, event_ref: "example:44" } },
      { id: "vault", label: "Vault", group: "Yours" },
      { id: "consents", label: "Consents", count: { value: 1, event_ref: "example:44" } },
      { id: "wiring", label: "Wiring" },
    ],
    presence: [{ label: "A" }, { label: "B" }, { label: "C" }],
    stage: { path: "/stage" },
    canvas: "content",
    dock: "dock",
    tray: "tray",
  },
  SplitView: {
    items: [
      { id: "t1", label: "Task 1" },
      { id: "t2", label: "Task 2" },
    ],
    selected: "t1",
    detail: ["content"],
  },
  StageBar: {
    current: { path: "/stage" },
    stages: "Germinate|Gather|Negotiate|Decide|Act|Live|Dissolve",
  },
  TopBar: {
    title: "Coalition 1",
    stage: { path: "/stage" },
    presence: [{ label: "A" }, { label: "B" }, { label: "C" }],
    actions: { value: 3, event_ref: "example:44" },
  },
  VoiceTurn: {
    script:
      "Two plans. The first keeps you together and costs about ninety-six euros. Say first, second, or tell me more.",
    choices: [
      { words: ["first"], value: "p1" },
      { words: ["second"], value: "p2" },
    ],
    confirm: true,
    earcon: "decision",
  },
  WiringDrawer: {
    event_ref: "example:44",
    projection: {
      type: "decide",
      subject: { kind: "plan", id: "p1", revision: { value: 2, event_ref: "example:44" } },
      scope: "coalition",
      hash: "5d0a…e19",
    },
  },
};
export const groups = [
  ["RoomShell \u00b7 the wide door", ["RoomShell", "TopBar", "Deck", "StageBar", "AgentDock"]],
  ["Entry: start, join, accept the charter", ["EntryComposer", "InviteCard", "JoinScreen"]],
  [
    "The other three doors: compact, message, lens and voice",
    ["PhoneShell", "MessageDoor", "LensCard", "VoiceTurn"],
  ],
  [
    "Containers, page frames and docks",
    [
      "SplitView",
      "PageHeader",
      "ConsentTray",
      "WiringDrawer",
      "NotificationCenter",
      "AccountMenu",
      "BoardTemplate",
    ],
  ],
];
export const labels: Record<string, { props: string; events: string }> = {
  AccountMenu: {
    props: "agents \u00b7 appearance \u00b7 channels \u00b7 identity",
    events: "account.pick(id)",
  },
  AgentDock: { props: "agent \u00b7 composer \u00b7 messages", events: "agent.say(text)" },
  BoardTemplate: { props: "cards \u00b7 columns", events: "card.open(id)" },
  ConsentTray: {
    props:
      "requests[] {kind: plan | tension | commitment | charter, subject, revision, deadline} · sorted by deadline · stored on the host: survives reconnects",
    events: "consent.open(subject)",
  },
  Deck: { props: "sections \u00b7 selected", events: "deck.select(id)" },
  EntryComposer: {
    props: "attachments \u00b7 goal \u00b7 packs",
    events: "coalition.create(goal, pack?)",
  },
  InviteCard: {
    props: "channels \u00b7 expires \u00b7 invitation \u00b7 role",
    events: "invite.copy \u00b7 invite.revoke",
  },
  JoinScreen: {
    props: "charter \u00b7 inviter \u00b7 subject",
    events: "charter.accept \u2192 owner-signed decide \u00b7 observe",
  },
  LensCard: { props: "body \u00b7 eyebrow \u00b7 gestures \u00b7 title", events: "gesture(name)" },
  MessageDoor: { props: "choices \u00b7 receipt \u00b7 text", events: "reply(n) \u00b7 reply(?)" },
  NotificationCenter: {
    props: "items",
    events: "notification.open(ref) \u00b7 notifications.read",
  },
  PageHeader: {
    props: "actions \u00b7 crumbs \u00b7 eyebrow \u00b7 tabs \u00b7 title",
    events: "display only",
  },
  PhoneShell: { props: "header \u00b7 stack \u00b7 tabs", events: "tab.select" },
  RoomShell: {
    props:
      "canvas \u00b7 coalition \u00b7 deck \u00b7 dock \u00b7 presence \u00b7 stage \u00b7 tray",
    events: "deck.select(id) \u00b7 invite.open \u00b7 search.open",
  },
  SplitView: { props: "detail \u00b7 items \u00b7 selected", events: "split.select(id)" },
  StageBar: { props: "current \u00b7 stages", events: "display only" },
  TopBar: { props: "actions \u00b7 presence \u00b7 stage \u00b7 title", events: "display only" },
  VoiceTurn: {
    props: "choices \u00b7 confirm \u00b7 earcon \u00b7 script",
    events: "voice.choice(value) \u00b7 voice.more",
  },
  WiringDrawer: {
    props: "event_ref \u00b7 projection",
    events: "wiring.verify \u00b7 wiring.copy",
  },
};
