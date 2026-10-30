// SPDX-License-Identifier: Apache-2.0
// Zod APIs for the first batch of the coalitionkit/v0_9 catalog. Text props accept a literal or a
// {path} binding; numbers are only ever {value, event_ref}; events are named, never code.
import { CommonSchemas } from "@a2ui/web_core/v0_9";
import { z } from "zod";

const { DynamicString, DataBinding } = CommonSchemas;

/** A literal or a binding to the viewer's state. */
const lit = <T extends z.ZodTypeAny>(s: T) => z.union([s, DataBinding]);

export const Bound = z
  .object({ value: z.number().finite(), event_ref: z.string().min(1) })
  .strict();
// Plain numbers never travel as numbers (the host rejects an unbound number), so seats, gaps and
// column counts are strings on the wire and turned into numbers by the implementation.
export const Seat = z.enum(["1", "2", "3", "4", "5", "host", "steward"]);
const Person = z.object({ seat: Seat, label: z.string() });
export const Gap = z.enum(["4", "8", "12", "16"]);

const objective = z.object({
  name: z.string(),
  value: Bound,
  unit: z.string().optional(),
  better: z.enum(["lower", "higher"]).optional(),
});
const plan = z.object({
  id: z.string(),
  label: z.string(),
  short: z.string().optional(),
  objectives: z.array(objective).max(12),
  tag: z
    .object({
      label: z.string(),
      kind: z.enum(["measured", "vault", "signed", "model", "estimate", "example"]),
    })
    .optional(),
  people: z.array(Person).max(50).optional(),
  note: z.string().optional(),
  highlight: z.boolean().optional(),
});
const subject = z.object({ kind: z.string(), id: z.string(), revision: Bound });

export const apis = {
  ScopeBadge: {
    name: "ScopeBadge",
    schema: z.object({ audience: z.string(), redact: z.array(z.string()).max(16).optional() }),
  },
  TaskCard: {
    name: "TaskCard",
    schema: z.object({
      task_id: z.string(),
      title: DynamicString,
      assignee: Person.optional(),
      window: z.string().optional(),
      status: z.enum([
        "open",
        "negotiating",
        "proposed",
        "decided",
        "committed",
        "done",
        "withdrawn",
      ]),
      deps: z
        .object({
          waitsFor: z.array(z.string()).max(50).optional(),
          unblocks: z.array(z.string()).max(50).optional(),
        })
        .optional(),
      evidence: z.string().optional(),
    }),
  },
  NeedCard: {
    name: "NeedCard",
    schema: z.object({
      need_id: z.string(),
      owner: Person,
      text: DynamicString,
      state: z.enum(["open", "matched", "fulfilled", "withdrawn"]),
      offers: Bound.optional(),
      meta: z.string().optional(),
    }),
  },
  OfferCard: {
    name: "OfferCard",
    schema: z.object({
      offer_id: z.string(),
      what: DynamicString,
      from: z.string().optional(),
      target: z.string().optional(),
      cost: z
        .object({ amount: Bound, unit: z.string().optional(), kind: z.string().optional() })
        .optional(),
      expires: z.string().optional(),
      state: z.enum(["open", "accepted", "expired", "withdrawn"]),
      needsYou: z.boolean().optional(),
      scope: z.string().optional(),
    }),
  },
  Timeline: {
    name: "Timeline",
    schema: z.object({
      items: lit(
        z
          .array(
            z.object({
              when: z.string(),
              title: z.string(),
              assignee: z.string().optional(),
              state: z.enum(["done", "now", "next"]),
            }),
          )
          .max(200),
      ),
    }),
  },
  PlanCompare: {
    name: "PlanCompare",
    schema: z.object({
      plans: z.array(plan).max(8),
      rejected: z
        .array(z.object({ plan, reason: z.string() }))
        .max(8)
        .optional(),
      state: z.enum(["proposed", "decided", "superseded"]).optional(),
      proposal_set_id: z.string().optional(),
      decision_deadline: z.string().optional(),
      decidedId: z.string().optional(),
    }),
  },
  TensionCard: {
    name: "TensionCard",
    schema: z.object({
      tension_id: z.string(),
      title: DynamicString,
      options: z
        .array(
          z.object({ id: z.string(), label: z.string(), tradeoffs: z.array(z.string()).max(12) }),
        )
        .max(12),
      deciders: z.array(Person.extend({ answered: z.boolean().optional() })).max(50),
      answered: Bound,
      decision_deadline: z.string().optional(),
      state: z.enum(["open", "decided", "split", "expired"]).optional(),
      chosenId: z.string().optional(),
    }),
  },
  ConsentCard: {
    name: "ConsentCard",
    schema: z.object({
      subject,
      summary: DynamicString,
      yourPart: z.string().optional(),
      cost: z.string().optional(),
      consequenceOfNo: z.string().optional(),
      decision_deadline: z.string().optional(),
      state: z.enum(["open", "answered", "stale", "expired"]).optional(),
      answer: z.boolean().optional(),
      currentRevision: Bound.optional(),
      yesLabel: z.string().optional(),
      noLabel: z.string().optional(),
    }),
  },
  VoteTally: {
    name: "VoteTally",
    schema: z.object({
      title: DynamicString,
      rule: z.string().optional(),
      deciders: z
        .array(Person.extend({ answered: z.boolean(), answer: z.boolean().optional() }))
        .max(50),
      outcome: z.enum(["decided", "refused", "split", "expired"]).optional(),
      closed: z.boolean().optional(),
    }),
  },
  RippleBanner: {
    name: "RippleBanner",
    schema: z.object({
      ripple: z.object({
        by: z.string(),
        change: z.string(),
        invalidated: z.array(z.string()).max(500),
        untouched: z.array(z.string()).max(500),
      }),
    }),
  },
  LensCard: {
    name: "LensCard",
    schema: z.object({
      title: DynamicString,
      eyebrow: z.string().optional(),
      body: DynamicString.optional(),
      /** How many gesture hints the card shows (0 to 2). A string on the wire, like every count. */
      gestures: z.enum(["0", "1", "2"]).optional(),
    }),
  },
  ChangedValue: {
    name: "ChangedValue",
    schema: z.object({
      path: z.string().optional(),
      before: DynamicString.optional(),
      after: DynamicString,
      state: z.enum(["flash", "tinted", "seen"]).optional(),
    }),
  },
  ActivityStream: {
    name: "ActivityStream",
    schema: z.object({
      items: lit(
        z
          .array(
            z.object({
              seq: Bound.optional(),
              actor: Person,
              verb: z.string(),
              object: z.string().optional(),
              time: z.string(),
              live: z.boolean().optional(),
              aboutMe: z.boolean().optional(),
              decision: z.boolean().optional(),
            }),
          )
          .max(200),
      ),
    }),
  },
  LogStream: {
    name: "LogStream",
    schema: z.object({
      entries: lit(
        z
          .array(
            z.object({
              seq: Bound.optional(),
              ts: z.string(),
              type: z.string(),
              summary: z.string(),
              hash: z.string(),
              form: z.enum(["original", "projection", "receipt-only"]),
            }),
          )
          .max(500),
      ),
      selected: Bound.optional(),
    }),
  },
} as const;
