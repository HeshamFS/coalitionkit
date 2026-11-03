// SPDX-License-Identifier: Apache-2.0
// A scripted room for the gallery and the tests, with neutral words only. It is the Room type
// stepped through every phase, so the screen can be looked at before an engine is behind it.
// Nothing imports this from the live path.
import type { OpenRequest } from "../feed/agent";
import type { ViewerState } from "../feed/delta";
import type { Activity, BriefItem, Room, RoomNeed, RoomResult, RoomSeat } from "./room";

export type Scene = {
  id: string;
  name: string;
  room: Room;
  state: ViewerState;
  requests: OpenRequest[];
};

const CATALOG = "coalitionkit/v0_9";
const open = (
  id: string,
  components: Record<string, unknown>[],
  data?: Record<string, unknown>,
) => [
  { version: "v0.9", createSurface: { surfaceId: id, catalogId: CATALOG } },
  { version: "v0.9", updateComponents: { surfaceId: id, components } },
  ...(data
    ? [{ version: "v0.9", updateDataModel: { surfaceId: id, path: "/", value: data } }]
    : []),
];

const table = (id: string, columns: [string, string][], rows: Record<string, string>[]) =>
  open(
    id,
    [
      {
        id: "root",
        component: "Table",
        rows: { path: "/rows" },
        columns: columns.map(([key, label]) => ({ key, label, sortable: false })),
      },
    ],
    { rows: rows.map((r, i) => ({ id: `r${i}`, ...r })) },
  );

export const people = (me: { signed: boolean }): RoomSeat[] => [
  {
    seat: "p1",
    role: "member",
    label: "Member 1",
    kind: "person",
    you: false,
    signed: true,
    state: "seated",
  },
  {
    seat: "p2",
    role: "member",
    label: "Member 2",
    kind: "person",
    you: false,
    signed: true,
    state: "seated",
  },
  {
    seat: "p3",
    role: "member",
    label: "Member 3",
    kind: "person",
    you: false,
    signed: false,
    state: "arriving",
  },
  {
    seat: "p4",
    role: "member",
    label: "Member 4",
    kind: "open",
    you: false,
    signed: false,
    state: "",
  },
  {
    seat: "p5",
    role: "member",
    label: "You",
    kind: "person",
    you: true,
    signed: me.signed,
    state: me.signed ? "seated" : "here",
  },
];

export const NEEDS: RoomNeed[] = [
  ["n1", "The place", "place"],
  ["n2", "The days", "schedule"],
  ["n3", "The budget", "budget"],
  ["n4", "The list", "list"],
  ["n5", "The invitation", "draft"],
].map(([id, title, kind]) => ({
  id: id as string,
  title: title as string,
  kind: kind as RoomNeed["kind"],
  detail: "",
  status: "",
  offers: 0,
  assignee: null,
  result: null,
  source: "model" as const,
}));

export const act = (a: Partial<Activity> & Pick<Activity, "id" | "verb" | "label">): Activity => ({
  at: `2026-11-03T10:00:${a.id.slice(1).padStart(2, "0")}Z`,
  seat: null,
  need: null,
  state: "done",
  ms: 1200,
  source: "model",
  event: null,
  ...a,
});

export const BRIEF: BriefItem[] = [
  {
    id: "q1",
    ask: "When could you help?",
    why: "Your agent compares this with the others without showing them.",
    component: "ChoicePicker",
    status: "open",
    messages: open(
      "q1",
      [
        {
          id: "root",
          component: "ChoicePicker",
          multiple: true,
          display: "chips",
          value: { path: "/value" },
          options: [
            { id: "d1", label: "Day 1" },
            { id: "d2", label: "Day 2" },
            { id: "d3", label: "Day 3" },
          ],
        },
      ],
      { value: ["d1"] },
    ),
  },
  {
    id: "q2",
    ask: "How much can you put in?",
    why: "Others never see this number.",
    component: "Slider",
    status: "open",
    messages: open(
      "q2",
      [
        {
          id: "root",
          component: "Slider",
          label: "Up to",
          unit: "units",
          value: { path: "/value" },
        },
      ],
      { value: 40 },
    ),
  },
  {
    id: "q3",
    ask: "What can you bring?",
    why: "Your agent offers only what you tick.",
    component: "ChoicePicker",
    status: "open",
    messages: open(
      "q3",
      [
        {
          id: "root",
          component: "ChoicePicker",
          multiple: true,
          display: "chips",
          value: { path: "/value" },
          options: [
            { id: "b1", label: "Tables" },
            { id: "b2", label: "A van" },
            { id: "b3", label: "Time on the day" },
          ],
        },
      ],
      { value: [] },
    ),
  },
];

export const RESULTS: RoomResult[] = [
  {
    id: "r1",
    need_id: "n1",
    kind: "place",
    title: "The place",
    by: "p1",
    seq: 14,
    source: "model",
    sources: ["e2", "e4"],
    tree: [{ component: "Table", props: { rows: "/rows" } }],
    data: {
      rows: [
        { what: "Where", detail: "Venue 1" },
        { what: "Days", detail: "Day 1 to Day 3" },
      ],
    },
    messages: table(
      "r1",
      [
        ["what", "What"],
        ["detail", "Detail"],
      ],
      [
        { what: "Where", detail: "Venue 1" },
        { what: "Days", detail: "Day 1 to Day 3" },
      ],
    ),
    replaced_by: null,
  },
  {
    id: "r2",
    need_id: "n2",
    kind: "schedule",
    title: "The days",
    by: "p5",
    seq: 16,
    source: "rules",
    sources: ["e2", "e3"],
    tree: [{ component: "Table", props: { rows: "/rows" } }],
    data: {
      rows: [
        { title: "Set up", start: "2026-11-07T09:00:00Z", end: "2026-11-07T12:00:00Z" },
        { title: "Open", start: "2026-11-08T10:00:00Z", end: "2026-11-08T16:00:00Z" },
      ],
    },
    messages: table(
      "r2",
      [
        ["title", "Day"],
        ["start", "Starts"],
      ],
      [
        { title: "Set up", start: "Day 1, 09:00" },
        { title: "Open", start: "Day 2, 10:00" },
      ],
    ),
    replaced_by: null,
  },
  {
    id: "r3",
    need_id: "n3",
    kind: "budget",
    title: "The budget",
    by: "p2",
    seq: 18,
    source: "model",
    sources: ["e3", "e4"],
    tree: [{ component: "Table", props: { rows: "/rows" } }],
    data: {
      rows: [
        { item: "Materials", paid_by: "Shared", cost: { value: 120, event_ref: "e3" } },
        { item: "Snacks", paid_by: "Shared", cost: { value: 60, event_ref: "e4" } },
      ],
    },
    messages: table(
      "r3",
      [
        ["item", "Item"],
        ["paid_by", "Paid by"],
        ["cost", "Cost"],
      ],
      [
        { item: "Materials", paid_by: "Shared", cost: "120" },
        { item: "Snacks", paid_by: "Shared", cost: "60" },
      ],
    ),
    replaced_by: null,
  },
];

export const TASKS = (done: boolean) => [
  {
    task_id: "t1",
    title: "Bring the tables",
    status: done ? "done" : "committed",
    result: null,
    can_mark_done: !done,
  },
  {
    task_id: "t2",
    title: "Send the invitation",
    status: "committed",
    result: "r2",
    can_mark_done: true,
  },
];

export const events = (plans: boolean): Record<string, unknown> => ({
  e1: { type: "coalition.charter", seq: 1, payload: { goal: "Goal 1" } },
  e2: { type: "coalition.offer", seq: 11, payload: {} },
  e3: { type: "coalition.offer", seq: 12, payload: {} },
  e4: { type: "coalition.match", seq: 24, payload: {} },
  ...(plans
    ? {
        e5: {
          type: "coalition.propose",
          seq: 26,
          payload: {
            plans: [
              {
                plan_id: "p1",
                title: "Everyone together",
                objective_scores: { total_cost: 36, max_share_ratio: 1, missed_days: 0 },
              },
              {
                plan_id: "p2",
                title: "Cheapest",
                objective_scores: { total_cost: 14, max_share_ratio: 1.4, missed_days: 1 },
              },
              {
                plan_id: "p3",
                title: "Smaller, closer",
                objective_scores: { total_cost: 22, max_share_ratio: 1, missed_days: 2 },
              },
            ],
          },
        },
      }
    : {}),
});

export const base = (over: Partial<Room>): Room => ({
  phase: "gather",
  lights: "day",
  goal: "Get one shared piece of work done by Friday, with four members and a shared budget",
  seats: people({ signed: true }),
  needs: NEEDS,
  activity: [],
  slots: [
    { id: "s1", label: "Day 1" },
    { id: "s2", label: "Day 2" },
    { id: "s3", label: "Day 3" },
  ],
  common: null,
  plan_notes: {},
  results: [],
  stops: [],
  checked: 0,
  change: null,
  begin: null,
  mine: { brief: [], feed: [], for_you: {}, tasks: [] },
  ...over,
});

export const ask = (kind: string, subject: string, message: string): OpenRequest => ({
  id: `${kind}:${subject}:1:p5`,
  kind,
  subjectId: subject,
  revision: 1,
  message,
});

export const seatsDone = people({ signed: true }).map((s) =>
  s.kind === "open"
    ? {
        ...s,
        kind: "helper" as const,
        label: "Budget helper",
        state: "agent, seated",
        signed: true,
      }
    : { ...s, signed: true, state: "seated" },
);
