// SPDX-License-Identifier: Apache-2.0
// Result trees shaped like the engine's own: `fixed_tree` and `fixed_body` in
// `room/results.py` (a Column holding a Heading, a muted caption and one Card per group of lines,
// each Card with a title, `fields` of label and value, and its provenance once at card level).
// The words are neutral; the structure and the `data` shapes follow the contract's table.
import type { RoomResult } from "./room";

type Doc = Record<string, unknown>;

const card = (index: number, title: string, fields: Doc[], prov: string): Doc => ({
  id: `fx${index}`,
  component: "Card",
  title,
  fields,
  provenance: prov,
});

const tree = (title: string, detail: string, body: Doc[]): unknown[] => {
  // The draft's own text sits inside its card (`fxb`), so every other node is a top-level child.
  const top = body.filter((n) => n.id !== "fxb").map((n) => n.id);
  return [
    { id: "root", component: "Column", gap: "12", children: ["h", "d", ...top] },
    { id: "h", component: "Heading", text: title, variant: "h2" },
    { id: "d", component: "Text", text: detail, variant: "caption", tone: "muted" },
    ...body,
  ];
};

const messages = (id: string, components: unknown[]): unknown[] => [
  { version: "v0.9", createSurface: { surfaceId: id, catalogId: "coalitionkit/v0_9" } },
  { version: "v0.9", updateComponents: { surfaceId: id, components } },
];

const bound = (value: number, ref: string) => ({ value, event_ref: ref });

const base = (
  over: Partial<RoomResult> & Pick<RoomResult, "id" | "need_id" | "kind" | "title">,
) => ({
  by: "p1",
  seq: 14,
  source: "model" as const,
  sources: ["e2", "e4"],
  seqs: [11, 24],
  tree: [],
  data: null,
  messages: [],
  replaced_by: null,
  ...over,
});

function make(
  r: Pick<RoomResult, "id" | "need_id" | "kind" | "title"> & Partial<RoomResult>,
  detail: string,
  body: Doc[],
): RoomResult {
  const components = tree(r.title, detail, body);
  return base({ ...r, tree: components, messages: messages(`result-${r.id}`, components) });
}

export const placeData = {
  options: [
    {
      name: "Venue 1",
      why: "Free on all three days",
      check: "Ask about step-free access",
      provenance: "estimate",
    },
    { name: "Venue 2", why: "Closer, one day short", check: "", provenance: "estimate" },
  ],
  chosen: null,
};

export const scheduleData = {
  items: [
    {
      title: "Set up",
      start: "2026-11-07T09:00:00Z",
      end: "2026-11-07T12:00:00Z",
      where: "Venue 1",
    },
    { title: "Open", start: "2026-11-08T10:00:00Z", end: "2026-11-08T16:00:00Z", where: "Venue 1" },
  ],
  steps: ["Book the venue", "Send the invitation"],
};

export const budgetData = {
  currency: "EUR",
  amount: 300,
  rows: [
    { label: "Materials", amount: 120, who: "Shared", provenance: "estimate" },
    { label: "Snacks", amount: 60, who: "Member 2", provenance: "estimate" },
  ],
  how_shared: "Split evenly between the five of you.",
  time: [
    { label: "Member 1", amount: 90, provenance: "signed", ref: "e3" },
    { label: "Member 2", amount: 45, provenance: "signed", ref: "e4" },
  ],
  time_total: 135,
  suggested: [{ label: "Table hire", amount: 40, unit: "EUR", provenance: "estimate" }],
  total: 180,
};

export const listData = {
  items: [
    { label: "Tables", who: "Member 1", provenance: "signed" },
    { label: "A van", who: "Member 2", provenance: "signed" },
  ],
};

export const draftData = {
  subject: "You are invited",
  body: "Come along on Saturday.\nBring a friend.",
};

const body = {
  place: [
    ...placeData.options.map((o, i) =>
      card(
        i,
        o.name,
        [
          { label: "Why it fits", value: o.why },
          ...(o.check ? [{ label: "Check first", value: o.check }] : []),
        ],
        "estimate",
      ),
    ),
  ],
  schedule: [
    ...scheduleData.items.map((s, i) =>
      card(
        i,
        s.title,
        [
          { label: "Start", value: s.start },
          { label: "End", value: s.end },
          { label: "Where", value: s.where },
        ],
        "signed",
      ),
    ),
    card(
      2,
      "Order of steps",
      scheduleData.steps.map((t, n) => ({ label: `Step ${n + 1}`, value: t })),
      "estimate",
    ),
  ],
  budget: [
    card(
      0,
      "Budget of 300 EUR",
      [
        ...budgetData.rows.map((r) => ({
          label: r.label,
          value: `${r.amount} EUR (${r.who})`,
        })),
        { label: "Total", value: "180 EUR" },
      ],
      "estimate",
    ),
    { id: "fxs", component: "Text", text: budgetData.how_shared },
    card(
      1,
      "Time people offered, in minutes",
      budgetData.time.map((t) => ({ label: t.label, value: bound(t.amount, t.ref) })),
      "signed",
    ),
  ],
  list: [
    card(
      0,
      "Who brings what",
      listData.items.map((i) => ({ label: i.label, value: i.who })),
      "signed",
    ),
  ],
  draft: [
    {
      id: "fx0",
      component: "Card",
      title: draftData.subject,
      provenance: "estimate",
      children: ["fxb"],
    },
    { id: "fxb", component: "Text", text: draftData.body },
  ],
};

/** A place result with no option named: the engine says so in a card of its own. */
export const emptyPlace = make(
  {
    id: "r1e",
    need_id: "n1",
    kind: "place",
    title: "The place",
    data: { options: [], chosen: null },
  },
  "Where it could happen",
  [
    card(
      0,
      "No place has been named yet",
      [
        {
          label: "To name one",
          value: "Say a place in the Say box, for example: the hall is free on Saturday.",
        },
      ],
      "signed",
    ),
  ],
);

export const ENGINE_RESULTS: RoomResult[] = [
  make(
    { id: "r1", need_id: "n1", kind: "place", title: "The place", by: "p1", data: placeData },
    "Where it could happen",
    body.place,
  ),
  make(
    {
      id: "r2",
      need_id: "n2",
      kind: "schedule",
      title: "The days",
      by: "p5",
      seq: 16,
      source: "rules",
      seqs: [11, 12],
      sources: ["e2", "e3"],
      data: scheduleData,
    },
    "When it happens",
    body.schedule,
  ),
  make(
    {
      id: "r3",
      need_id: "n3",
      kind: "budget",
      title: "The budget",
      by: "p2",
      seq: 18,
      seqs: [12, 24],
      sources: ["e3", "e4", "e6"],
      data: budgetData,
    },
    "What it costs",
    body.budget,
  ),
  make(
    { id: "r4", need_id: "n4", kind: "list", title: "The list", by: "p3", seq: 20, data: listData },
    "Who brings what",
    body.list,
  ),
  make(
    {
      id: "r5",
      need_id: "n5",
      kind: "draft",
      title: "The invitation",
      by: "p4",
      seq: 22,
      data: draftData,
    },
    "The words to send",
    body.draft,
  ),
];
