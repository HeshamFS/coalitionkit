// SPDX-License-Identifier: Apache-2.0
import type { Data } from "./ui";

const bound = (value: number) => ({ value, event_ref: "example:44" });
export const sheetData: Record<string, Data> = {
  RoomShell: {
    coalition: "Working in Group 1",
    presence: [
      { label: "A", agents: bound(2) },
      {
        label: "B",
        agents: bound(1),
        cursor: {
          x: bound(330),
          y: bound(190),
          seat: bound(2),
          label: "B's agent",
          connection: {
            from: { x: bound(150), y: bound(128) },
            to: { x: bound(175), y: bound(168) },
          },
        },
      },
      { label: "C", agents: bound(1), presence: "away" },
    ],
  },
  MessageDoor: {
    text: "Two plans for Task 1 by 10:00.\n\nDecide by 22:40.",
    choices: [
      {
        n: bound(1),
        label: "Together on the 07:10, resource near P1, task 22:45. About €96 for you.",
        value: "p1",
        selected: true,
        confirmation:
          "Signed with your key. Waiting for 1 more person. I'll message you only if something needs you.",
      },
      { n: bound(2), label: "Split: you on the 09:40. About €71.", value: "p2" },
    ],
    receipt: "#44 · coalitionkit.dev/l/44",
  },
  VoiceTurn: {
    script:
      "Two plans. The first keeps you together on the seven-ten and costs about ninety-six euros. The second splits you up and costs about seventy-one. Say first, second, or tell me more.",
    choices: [
      { words: ["first"], value: "p1", transcript: '"first" → decide(plan A), owner-signed' },
      { words: ["second"], value: "p2" },
    ],
  },
  WiringDrawer: {
    event_ref: "#43",
    projection: {
      seq: bound(43),
      time: "22:19:07",
      prev_hash: "9c1e…a07",
      receipt: "receipt ✓ host ed25519",
      verified: true,
      inspected: { title: "Task at Place 1", summary: "starts 22:45" },
      event: {
        type: "coalition.ripple",
        on_behalf_of: "p2",
        scope: { audience: "task:t3" },
        payload: { invalidates: ["t3"] },
      },
    },
  },
  EntryComposer: {
    attachments: [{ label: "request.pdf" }],
    packs: ["Shared project", "Resource coordination", "Community help"],
  },
  JoinScreen: {
    inviter: "Member A",
    charter: {
      title: "Working together in Group 1",
      summary:
        "Goal: finish Task 1 by 10:00 tomorrow, together if it costs no more than going alone.",
      rules: [
        "Your vault answers yes or no; numbers stay with you",
        "Every member decides each plan",
        "Budget for agents: €2 for the whole coalition",
        { text: "The host keeps a signed log you can read", tone: "warn" },
      ],
    },
    subject: { kind: "charter", id: "c1", revision: bound(3) },
  },
  AccountMenu: {
    identity: { label: "Member A", kid: "3b9e…71f" },
    agents: [
      { id: "a1", label: "Your agent" },
      { id: "a2", label: "Your second agent" },
    ],
    channels: ["web", "WhatsApp"],
  },
  BoardTemplate: {
    columns: [
      { id: "open", label: "Open" },
      { id: "negotiating", label: "Negotiating" },
      { id: "decided", label: "Decided" },
      { id: "done", label: "Done" },
    ],
    cards: [
      { id: "t1", title: "Resource before 01:00", status: "open", meta: "need · B" },
      { id: "t2", title: "Prepare resource", status: "open", meta: "need · C" },
      {
        id: "t3",
        title: "Task at Place 1",
        status: "negotiating",
        people: ["A", "B"],
        offers: "2 offers",
      },
      { id: "t4", title: "Start at 07:10", status: "decided" },
    ],
  },
  NotificationCenter: {
    items: [
      {
        text: "Member B moved the task date",
        emphasis: "Member B",
        count: bound(3),
        time: "2 min",
        summary: "ripple on 2 tasks",
        ref: "t3",
        read: false,
      },
      {
        text: "Plan A needs your answer",
        emphasis: "needs your answer",
        time: "5 min",
        summary: "deadline 22:40",
        ref: "p1",
        read: false,
      },
      { text: "The steward redacted one field", time: "21:52", ref: "event:42", read: true },
    ],
  },
  PageHeader: {
    title: "Work together",
    eyebrow: "Plan · revision 2",
    crumbs: ["Group 1", "Plans", "Plan A"],
    tabs: ["Overview", { label: "Tasks", count: bound(6) }, "Costs", "Log"],
  },
  SplitView: {
    items: [
      { id: "p1", label: "Plan A" },
      { id: "p2", label: "Plan B" },
      { id: "p3", label: "Plan C", badge: "new" },
    ],
    selected: "p1",
    detail: ["detail-title", "detail-fields", "detail-actions"],
  },
};
export const sheetLabels: Record<string, string> = {
  RoomShell:
    "fixed: TopBar (coalition, StageBar, presence, search, invite, me) · Deck (sections, counts) · Canvas (generated) · AgentDock (private chat) · ConsentTray · WiringDrawer toggle. Everything on the canvas is an A2UI tree for this viewer.",
  EntryComposer:
    "goal (text | voice) · attachments → vault · suggested packs[] · submit → charter draft by the organizer's agent",
  InviteCard:
    "invitation (single use, bound to participant + card) · role · expires · channels: link | QR | WhatsApp | agent card URL",
  JoinScreen:
    "charter summary (from charter, rev) · rules[] {text, tone} · accept → owner-signed decide(charter) · watch → observe",
  PhoneShell:
    "header (coalition, stage, presence) · stack of generated cards, one action each · tab bar: Now | Plans | People | Agent · 44 px targets",
  MessageDoor:
    'text only, ≤ 1 024 chars · numbered choices · "?" opens the agent · consent answered in-thread is still owner-signed · receipt link',
  LensCard:
    "one card, one step · text ≥ 18 px, white on 78 % black · ≤ 2 actions mapped to gestures · never a consent for money (hands off to phone)",
  VoiceTurn:
    "script (≤ 3 sentences) · choices[] {words[], value} · confirm step required for consent · earcon · barge-in",
  Card: "title · leading? · status · meta · fields[] {label, value, provenance} · actions[] ≤ 3 · scope · variant: default | live | ask | dashed",
  Panel:
    "Panel: title · count · action · body · Grid: columns 1-4 (by door) · gap 6 | 12 · Section: label rule like this sheet",
  SplitView: "items[] · selected · detail (components) · collapses to push navigation on compact",
  PageHeader: "crumbs[] · eyebrow · title · actions[] ≤ 2 · tabs? · sticky on scroll",
  ConsentTray:
    "requests[] {kind: plan | tension | commitment | charter, subject, revision, deadline} · sorted by deadline · stored on the host: survives reconnects",
  WiringDrawer:
    "event_ref · shows the viewer's own projection of the event (never more) · verify: signature, hash link, receipt",
  NotificationCenter:
    'items[] {kind, text, time, ref, read} · grouped by coalition · channel echo: WhatsApp only for "needs you"',
  AccountMenu:
    "identity · agents[] · vault · channels · appearance: light | dark | system · export · sign out",
  BoardTemplate:
    "columns from task status (open → negotiating → proposed → decided → committed → done) · cards are TaskCards · drag disabled: status moves only by protocol events",
};

const qrCells = [
  [1, 1, 7, 7, 0],
  [21, 1, 7, 7, 0],
  [1, 21, 7, 7, 0],
  [2, 2, 5, 5, 1],
  [22, 2, 5, 5, 1],
  [2, 22, 5, 5, 1],
  [3, 3, 3, 3, 0],
  [23, 3, 3, 3, 0],
  [3, 23, 3, 3, 0],
  [10, 2, 2, 1, 0],
  [13, 3, 1, 3, 0],
  [16, 1, 2, 2, 0],
  [10, 6, 3, 2, 0],
  [15, 5, 2, 3, 0],
  [2, 10, 2, 2, 0],
  [6, 11, 3, 1, 0],
  [10, 10, 2, 3, 0],
  [13, 9, 3, 2, 0],
  [18, 10, 2, 2, 0],
  [21, 11, 3, 1, 0],
  [25, 10, 3, 2, 0],
  [11, 14, 1, 3, 0],
  [14, 13, 2, 2, 0],
  [17, 14, 3, 1, 0],
  [22, 14, 2, 3, 0],
  [2, 15, 3, 1, 0],
  [6, 16, 2, 2, 0],
  [10, 18, 3, 2, 0],
  [15, 17, 2, 3, 0],
  [19, 18, 2, 1, 0],
  [24, 18, 3, 2, 0],
  [10, 22, 2, 2, 0],
  [13, 23, 3, 1, 0],
  [18, 21, 2, 3, 0],
  [21, 23, 3, 2, 0],
  [25, 22, 2, 3, 0],
  [11, 26, 3, 2, 0],
  [16, 25, 2, 2, 0],
  [20, 26, 3, 1, 0],
];
export const inviteIllustration = qrCells.map(([x = 0, y = 0, w = 1, h = 1, light]) => ({
  x: bound(x),
  y: bound(y),
  w: bound(w),
  h: bound(h),
  light: Boolean(light),
}));
