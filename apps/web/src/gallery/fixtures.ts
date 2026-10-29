// SPDX-License-Identifier: Apache-2.0
// Neutral fixtures for the gallery and the tests. Names are roles and numbers, never real people.
import type { Plan } from "../components/plans";
import type { Participant } from "../components/work";

export const m1: Participant = { seat: 1, label: "Member 1" };
export const m2: Participant = { seat: 2, label: "Member 2" };
export const m3: Participant = { seat: 3, label: "Member 3" };
export const m4: Participant = { seat: 4, label: "Member 4" };
export const m5: Participant = { seat: 5, label: "Member 5" };
export const people = [m1, m2, m3];

const ref = (n: number) => ({ value: n, event_ref: `e${n}` });

export const planA: Plan = {
  id: "p1",
  label: "Plan A",
  short: "A",
  tag: { label: "fastest", kind: "signed" },
  highlight: true,
  objectives: [
    { name: "Time", value: ref(8), unit: "h" },
    { name: "Cost", value: ref(158) },
    { name: "Max load", value: ref(41), unit: "%" },
  ],
  people,
  note: "6 tasks, all members",
};
export const planB: Plan = {
  id: "p2",
  label: "Plan B",
  short: "B",
  tag: { label: "cheapest", kind: "estimate" },
  objectives: [
    { name: "Time", value: ref(15), unit: "h" },
    { name: "Cost", value: ref(92) },
    { name: "Max load", value: ref(40), unit: "%" },
  ],
  people,
  note: "6 tasks, slower path",
};
export const planC: Plan = {
  id: "p3",
  label: "Plan C",
  objectives: [
    { name: "Time", value: ref(11), unit: "h" },
    { name: "Cost", value: ref(110) },
    { name: "Max load", value: ref(72), unit: "%" },
  ],
};

export const bound = (n: number, id = `e${n}`) => ({ value: n, event_ref: id });

export const logEntries = [
  {
    seq: 51,
    ts: "t+00",
    type: "coalition.propose",
    summary: "Member 1 sent 2 plans",
    hash: "9c1e…",
    form: "original" as const,
  },
  {
    seq: 52,
    ts: "t+02",
    type: "coalition.decide",
    summary: "Member 2 yes, Plan A r2",
    hash: "41d0…",
    form: "original" as const,
  },
  {
    seq: 53,
    ts: "t+09",
    type: "coalition.decide",
    summary: "Member 3 yes, Plan A r2",
    hash: "e7a2…",
    form: "original" as const,
  },
  {
    seq: 54,
    ts: "t+12",
    type: "coalition.projection",
    summary: "host, your view of #53",
    hash: "aa31…",
    form: "projection" as const,
  },
  {
    seq: 56,
    ts: "t+18",
    type: "coalition.decide",
    summary: "",
    hash: "07bf…",
    form: "receipt-only" as const,
  },
];

export const activity = [
  {
    seq: 61,
    actor: m2,
    verb: "changed",
    object: "task t2",
    time: "now",
    live: true,
    aboutMe: true,
  },
  {
    seq: 60,
    actor: { seat: "host" as const, label: "Planner" },
    verb: "is re-planning",
    object: "4 tasks",
    time: "now",
  },
  { seq: 59, actor: m3, verb: "answered", object: "query q14 (vault)", time: "2 m", aboutMe: true },
  {
    seq: 58,
    actor: { seat: "steward" as const, label: "Steward" },
    verb: "redacted",
    object: "1 field",
    time: "6 m",
  },
  { seq: 57, actor: m1, verb: "accepted", object: "Plan A", time: "11 m", decision: true },
];

export const wireMessage = {
  type: "coalition.ripple",
  on_behalf_of: "p2",
  scope: { audience: "task:t3" },
  payload: { invalidates: ["t3"] },
};
