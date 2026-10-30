// SPDX-License-Identifier: Apache-2.0
// Zod APIs for the first batch of the coalitionkit/v0_9 catalog. Text props accept a literal or a
// {path} binding; numbers are only ever {value, event_ref}; events are named, never code.
import { CommonSchemas } from "@a2ui/web_core/v0_9";
import { z } from "zod";

const { DynamicString, DynamicBoolean, ChildList, Action, DataBinding } = CommonSchemas;

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
const Icons = z.enum(["inbox", "info", "check", "clock", "people", "list", "lock", "shield"]);

const subject = z.object({ kind: z.string(), id: z.string(), revision: Bound });

export const apis = {
  Text: {
    name: "Text",
    schema: z.object({
      text: DynamicString,
      variant: z.enum(["body", "caption"]).optional(),
      tone: z.enum(["default", "muted", "blue"]).optional(),
      provenance: z.string().optional(),
    }),
  },
  Heading: {
    name: "Heading",
    schema: z.object({
      text: DynamicString,
      variant: z.enum(["h1", "h2", "h3"]).optional(),
      tone: z.enum(["default", "blue"]).optional(),
    }),
  },
  Row: {
    name: "Row",
    schema: z.object({
      children: ChildList,
      gap: Gap.optional(),
      align: z.enum(["start", "center", "end"]).optional(),
    }),
  },
  Column: { name: "Column", schema: z.object({ children: ChildList, gap: Gap.optional() }) },
  Grid: {
    name: "Grid",
    schema: z.object({
      children: ChildList,
      columns: z.enum(["1", "2", "3", "4"]).optional(),
      gap: Gap.optional(),
    }),
  },
  Card: {
    name: "Card",
    schema: z.object({
      children: ChildList.optional(),
      title: DynamicString.optional(),
      tone: z.enum(["default", "live", "ask", "dashed"]).optional(),
      scope: z.string().optional(),
      /** Label and value pairs; the fixed fallback layout fills this from the viewer's state. */
      fields: lit(z.array(z.object({ label: z.string(), value: z.string() })).max(50)).optional(),
      subject: subject.optional(),
    }),
  },
  Panel: {
    name: "Panel",
    schema: z.object({
      children: ChildList.optional(),
      title: DynamicString.optional(),
      scope: z.string().optional(),
    }),
  },
  Button: {
    name: "Button",
    schema: z.object({
      label: DynamicString,
      variant: z
        .enum(["primary", "secondary", "ink", "ghost", "soft", "danger", "danger-fill"])
        .optional(),
      size: z.enum(["sm", "md", "lg"]).optional(),
      action: Action.optional(),
      disabled: DynamicBoolean.optional(),
      busy: DynamicBoolean.optional(),
    }),
  },
  Tag: {
    name: "Tag",
    schema: z.object({
      label: DynamicString.optional(),
      kind: z.enum(["agreed", "needs", "changed", "private", "blocked"]),
    }),
  },
  Badge: {
    name: "Badge",
    schema: z.object({
      label: DynamicString,
      kind: z.enum(["measured", "vault", "signed", "model", "estimate", "example"]).optional(),
    }),
  },
  ScopeBadge: {
    name: "ScopeBadge",
    schema: z.object({ audience: z.string(), redact: z.array(z.string()).max(16).optional() }),
  },
  Avatar: {
    name: "Avatar",
    schema: z.object({
      seat: Seat,
      label: z.string(),
      presence: z.enum(["live", "away", "off"]).optional(),
      ring: z.boolean().optional(),
      size: z.enum(["xs", "sm", "lg", "xl"]).optional(),
    }),
  },
  AvatarStack: {
    name: "AvatarStack",
    schema: z.object({ people: z.array(Person).max(50), max: Bound.optional() }),
  },
  Banner: {
    name: "Banner",
    schema: z.object({
      tone: z.enum(["info", "ask", "blocked", "agreed"]),
      title: DynamicString,
      body: DynamicString.optional(),
      actionLabel: z.string().optional(),
      dismissible: z.boolean().optional(),
    }),
  },
  Toast: {
    name: "Toast",
    schema: z.object({
      tone: z.enum(["done", "change", "error"]),
      text: DynamicString,
      actionLabel: z.string().optional(),
      undoWindow: Bound.optional(),
    }),
  },
  EmptyState: {
    name: "EmptyState",
    schema: z.object({
      glyph: Icons.optional(),
      title: DynamicString,
      body: DynamicString,
      actionLabel: z.string().optional(),
    }),
  },
  ErrorState: {
    name: "ErrorState",
    schema: z.object({
      state: z.enum(["error", "reconnecting"]).optional(),
      cause: DynamicString,
      lastSeen: z.string().optional(),
      retry: z.boolean().optional(),
      details: z.object({ code: z.string(), ref: z.string() }).optional(),
      missed: Bound.optional(),
    }),
  },
  Skeleton: {
    name: "Skeleton",
    schema: z.object({
      shape: z.enum(["line", "block", "avatar", "card"]).optional(),
      lines: Bound.optional(),
      reserves: Bound.optional(),
      state: z.enum(["skeleton", "filled", "live", "rest", "changed"]).optional(),
      value: DynamicString.optional(),
      previous: DynamicString.optional(),
      provenance: z.string().optional(),
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
