// SPDX-License-Identifier: Apache-2.0
// A scripted room for the gallery and the tests, with neutral words only. It is the Room type
// stepped through every phase, so the screen can be looked at before an engine is behind it.
// Nothing imports this from the live path.

import type { OpenRequest } from "../feed/agent";
import type { ViewerState } from "../feed/delta";
import { ENGINE_RESULTS } from "./engineResults";
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

const bound = (value: number, ref = "e2") => ({ value, event_ref: ref });

/** A brief question's tree, exactly as the engine composes it (`brief.py: tree()`). */
const briefTree = (
  id: string,
  ask: string,
  why: string,
  field: Record<string, unknown>,
  answer: unknown,
) =>
  open(
    `brief-${id}`,
    [
      { id: "root", component: "Column", gap: "12", children: ["ask", "why", "input", "go"] },
      { id: "ask", component: "Heading", text: ask, variant: "h3" },
      {
        id: "why",
        component: "Text",
        text: why,
        variant: "caption",
        tone: "muted",
        provenance: "model",
      },
      { id: "input", ...field, value: { path: "/answer" } },
      {
        id: "go",
        component: "Button",
        label: "Send",
        variant: "primary",
        action: { name: "room.brief", context: { question_id: id, value: { path: "/answer" } } },
      },
    ],
    { answer },
  );

const chips = (opts: [string, string][], multiple: boolean) => ({
  component: "ChoicePicker",
  display: "chips",
  ...(multiple ? { multiple: true } : {}),
  options: opts.map(([id, label]) => ({ id, label })),
});

export const BRIEF: BriefItem[] = [
  {
    id: "q1",
    ask: "When could you help?",
    why: "Your agent compares this with the others without showing them.",
    component: "ChoicePicker",
    status: "open",
    messages: briefTree(
      "q1",
      "When could you help?",
      "Your agent compares this with the others without showing them.",
      chips(
        [
          ["s1", "Day 1 morning"],
          ["s2", "Day 1 afternoon"],
          ["s3", "Day 2 morning"],
          ["s4", "Day 2 afternoon"],
          ["s5", "Day 3 morning"],
          ["s6", "Day 3 afternoon"],
        ],
        true,
      ),
      [],
    ),
  },
  {
    id: "q2",
    ask: "How much can you put in?",
    why: "Others never see this number.",
    component: "Slider",
    status: "open",
    messages: briefTree(
      "q2",
      "How much can you put in?",
      "Others never see this number.",
      { component: "Slider", min: bound(0), max: bound(100), step: bound(5), unit: "units" },
      bound(50),
    ),
  },
  {
    id: "q3",
    ask: "What can you bring?",
    why: "Your agent offers only what you pick.",
    component: "ChoicePicker",
    status: "open",
    messages: briefTree(
      "q3",
      "What can you bring?",
      "Your agent offers only what you pick.",
      chips(
        [
          ["b1", "Tables"],
          ["b2", "A van"],
          ["b3", "Time on the day"],
        ],
        false,
      ),
      "",
    ),
  },
];

export const RESULTS: RoomResult[] = ENGINE_RESULTS;

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
  closes: "2026-11-06T22:59:00Z",
  seats: people({ signed: true }),
  needs: NEEDS,
  activity: [],
  slots: [
    { id: "s1", label: "Day 1 morning", start: "2026-11-07T09:00:00Z" },
    { id: "s2", label: "Day 1 afternoon", start: "2026-11-07T14:00:00Z" },
    { id: "s3", label: "Day 2 morning", start: "2026-11-08T09:00:00Z" },
    { id: "s4", label: "Day 2 afternoon", start: "2026-11-08T14:00:00Z" },
    { id: "s5", label: "Day 3 morning", start: "2026-11-09T09:00:00Z" },
    { id: "s6", label: "Day 3 afternoon", start: "2026-11-09T14:00:00Z" },
  ],
  common: null,
  plan_notes: {},
  results: [],
  stops: [],
  checked: 0,
  change: null,
  begin: null,
  measured: null,
  mine: { brief: [], brief_closes: null, asks: null, feed: [], for_you: {}, tasks: [] },
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
