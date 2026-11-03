// SPDX-License-Identifier: Apache-2.0
// The scripted scenes: the room stepped through every phase.
import type { Scene } from "./fixtures";
import {
  act,
  ask,
  BRIEF,
  base,
  events,
  NEEDS,
  people,
  RESULTS,
  seatsDone,
  TASKS,
} from "./fixtures";

const RAW: Scene[] = [
  {
    id: "arrive",
    name: "Arrive",
    room: base({
      seats: people({ signed: false }),
      activity: [
        act({
          id: "a1",
          verb: "planning",
          label: "The Gardener splits the goal into what really needs doing.",
          ms: 2300,
        }),
      ],
    }),
    state: { events: events(false), viewer: "p5" },
    requests: [ask("charter", "c1", "Take part in this coalition")],
  },
  {
    id: "seated",
    name: "Seated",
    room: base({ begin: { can: true, open_seats: 1 } }),
    state: { events: events(false), viewer: "p5" },
    requests: [],
  },
  {
    id: "brief",
    name: "Brief",
    room: base({
      phase: "brief",
      seats: seatsDone,
      activity: [
        act({
          id: "a2",
          verb: "asking",
          seat: "p1",
          label: "Member 1's agent asks its person.",
          state: "running",
          ms: null,
        }),
      ],
      mine: {
        brief: BRIEF,
        brief_closes: "2026-11-03T10:04:00Z",
        asks: null,
        feed: [],
        for_you: {},
        tasks: [],
      },
    }),
    state: { events: events(false), viewer: "p5" },
    requests: [],
  },
  {
    id: "work",
    name: "Agents work",
    room: base({
      phase: "work",
      lights: "night",
      seats: seatsDone,
      needs: NEEDS.map((n, i) => ({ ...n, offers: i < 3 ? 1 : 0, status: i < 3 ? "offered" : "" })),
      activity: [
        act({
          id: "a3",
          verb: "offering",
          seat: "p1",
          need: "n1",
          label: "Member 1's agent offers a place.",
          ms: 1800,
        }),
        act({
          id: "a4",
          verb: "offering",
          seat: "p2",
          need: "n3",
          label: "Member 2's agent offers to keep the books.",
          ms: 2100,
        }),
        act({
          id: "a5",
          verb: "offering",
          seat: "p5",
          need: "n2",
          label: "Your agent offers your days.",
          state: "running",
          ms: null,
        }),
      ],
      mine: {
        brief_closes: null,
        asks: null,
        brief: BRIEF.map((b) => ({ ...b, status: "answered" as const })),
        feed: [
          { at: "10:00", text: "I read the five needs." },
          { at: "10:01", text: "You can help on Day 1. I offered that." },
        ],
        for_you: {},
        tasks: [],
      },
    }),
    state: { events: events(false), viewer: "p5" },
    requests: [],
  },
  {
    id: "compare",
    name: "Compare",
    room: base({
      phase: "work",
      lights: "night",
      seats: seatsDone,
      needs: NEEDS.map((n) => ({ ...n, offers: 1, status: "offered" })),
      activity: [
        act({
          id: "a6",
          verb: "comparing",
          label: "Five vaults compare free time, blinded.",
          state: "running",
          ms: null,
          source: "host",
        }),
      ],
      common: { slots: ["s1"], count_private: 2, compared: 5 },
      stops: [
        {
          id: "x1",
          at: "2026-11-03T10:00:07Z",
          seat: "p3",
          to: "p5",
          policy: "no-contact-before-consent",
          explain: "A message asked for a phone number.",
        },
      ],
      mine: {
        brief_closes: null,
        asks: null,
        brief: [],
        feed: [{ at: "10:02", text: "Day 1 fits you. I shared nothing else." }],
        for_you: {},
        tasks: [],
      },
    }),
    state: { events: events(false), viewer: "p5" },
    requests: [],
  },
  {
    id: "plans",
    name: "Decide",
    room: base({
      phase: "decide",
      seats: seatsDone,
      activity: [
        act({ id: "a7", verb: "explaining", label: "The Gardener explains the plans.", ms: 900 }),
      ],
      plan_notes: {
        p1: {
          name: "Everyone together",
          line: "All five can come, all three days.",
          source: "model",
        },
        p2: { name: "Cheapest", line: "Lowest cost, one day missed.", source: "rules" },
        p3: { name: "Smaller, closer", line: "Two days, nearer to everyone.", source: "model" },
      },
      mine: {
        brief_closes: null,
        asks: null,
        brief: [],
        feed: [],
        for_you: {
          p1: "Day 1 morning, tables, 36 units",
          p2: "Day 2 morning, tables, 14 units",
          p3: "Day 1 afternoon, tables, 22 units",
        },
        tasks: [],
      },
    }),
    state: { events: events(true), viewer: "p5" },
    requests: [
      ask("plan", "p1", "Decide on plan A"),
      ask("plan", "p2", "Decide on plan B"),
      ask("plan", "p3", "Decide on plan C"),
    ],
  },
  {
    id: "commit",
    name: "Commit",
    room: base({ phase: "commit", seats: seatsDone, checked: 31 }),
    state: { events: events(true), viewer: "p5" },
    requests: [
      ask("commitment", "c1", "Commit to your part"),
      ask("task", "t1", "Bring the tables"),
    ],
  },
  {
    id: "make",
    name: "Agents do",
    room: base({
      phase: "make",
      lights: "night",
      seats: seatsDone,
      needs: NEEDS.map((n, i) => ({
        ...n,
        status: i < 3 ? "done" : "making",
        result: i < 3 ? `r${i + 1}` : null,
      })),
      activity: [
        act({
          id: "a8",
          verb: "making",
          seat: "p1",
          need: "n1",
          label: "Member 1's agent pins the place.",
          ms: 1400,
        }),
        act({
          id: "a9",
          verb: "making",
          seat: "p5",
          need: "n2",
          label: "Your agent lays out the days.",
          ms: 2600,
        }),
        act({
          id: "a10",
          verb: "making",
          seat: "p2",
          need: "n3",
          label: "Member 2's agent builds the budget.",
          ms: 3100,
        }),
        act({
          id: "a11",
          verb: "making",
          seat: "p4",
          need: "n4",
          label: "Member 4's agent turns the offers into a list.",
          state: "running",
          ms: null,
        }),
      ],
      results: RESULTS.slice(0, 3),
      checked: 36,
      mine: {
        brief_closes: null,
        asks: null,
        brief: [],
        feed: [{ at: "10:09", text: "I am laying out the days." }],
        for_you: {},
        tasks: TASKS(false),
      },
    }),
    state: { events: events(true), viewer: "p5" },
    requests: [],
  },
  {
    id: "live",
    name: "Your part",
    room: base({
      phase: "live",
      seats: seatsDone,
      needs: NEEDS.map((n, i) => ({
        ...n,
        status: "done",
        result: `r${i + 1}`,
      })),
      results: RESULTS,
      checked: 42,
      mine: {
        brief_closes: null,
        asks: null,
        brief: [],
        feed: [{ at: "10:12", text: "I need two things from you." }],
        for_you: {},
        tasks: TASKS(false),
      },
    }),
    state: { events: events(true), viewer: "p5" },
    requests: [],
  },
  {
    id: "change",
    name: "Change",
    room: base({
      phase: "live",
      seats: seatsDone,
      needs: NEEDS.map((n, i) => ({
        ...n,
        status: i === 1 || i === 3 ? "re-planning" : "done",
        result: i === 0 || i === 2 ? `r${i + 1}` : null,
      })),
      activity: [
        act({
          id: "a12",
          verb: "changing",
          seat: "p3",
          label: "Member 3 cannot come on Day 3. Only what it touches moves.",
          state: "running",
          ms: null,
          source: "host",
        }),
      ],
      results: RESULTS,
      change: {
        text: "Member 3 cannot come on Day 3.",
        from: "p3",
        moved: ["n2", "n4"],
        asked: ["p5"],
        untouched: 3,
      },
      checked: 46,
      mine: {
        brief: [],
        brief_closes: null,
        asks: null,
        feed: [],
        for_you: {},
        tasks: TASKS(false),
      },
    }),
    state: { events: events(true), viewer: "p5" },
    requests: [ask("commitment", "c2", "Take the Day 3 stand instead")],
  },
  {
    id: "ended",
    name: "Finish",
    room: base({ phase: "ended", seats: seatsDone, results: RESULTS, checked: 48 }),
    state: { events: events(true), viewer: "p5" },
    requests: [],
  },
];

/** The host's plain words for each ask, as `mine.asks` carries them. */
const SUMMARY: Record<string, string> = {
  "charter:c1":
    "Join this room and take your seat. You agree to the goal; your agent never decides for you.",
  "plan:p1": "Choose Everyone together as the plan.",
  "plan:p2": "Choose Cheapest as the plan.",
  "plan:p3": "Choose Smaller, closer as the plan.",
  "commitment:c1": "Take your part: bring the tables on Day 1.",
  "commitment:c2": "Take the Day 3 stand instead.",
};

/**
 * Every scene carries `mine.asks` the way the engine sends it: one plain line per request, and no
 * line for a task whose commitment is also waiting, since one yes closes both.
 */
export const SCENES: Scene[] = RAW.map((s) => ({
  ...s,
  room: {
    ...s.room,
    mine: {
      ...s.room.mine,
      asks: s.requests
        .filter((r) => r.kind !== "task")
        .map((r) => ({
          kind: r.kind,
          id: r.subjectId,
          revision: r.revision,
          summary: SUMMARY[`${r.kind}:${r.subjectId}`] ?? r.message,
        })),
    },
  },
}));
