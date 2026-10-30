// SPDX-License-Identifier: Apache-2.0
import { createComponentImplementation } from "@a2ui/react/v0_9";
import { CommonSchemas } from "@a2ui/web_core/v0_9";
import { z } from "zod";
import { render } from "../../components/f09/render";
import { Bound } from "../schemas";

const lit = <T extends z.ZodTypeAny>(schema: T) => z.union([schema, CommonSchemas.DataBinding]);
export const apis = {
  ActivityStream: {
    name: "ActivityStream",
    schema: z.object({
      filter: lit(z.enum(["all", "about me", "decisions"])).optional(),
      items: lit(z.array(z.unknown())).optional(),
    }),
  },
  CanvasPresence: {
    name: "CanvasPresence",
    schema: z.object({
      cursors: lit(z.array(z.unknown())).optional(),
    }),
  },
  ChainView: {
    name: "ChainView",
    schema: z.object({
      entries: lit(z.array(z.unknown())).optional(),
      genesis: lit(z.string()).optional(),
    }),
  },
  ChangedValue: {
    name: "ChangedValue",
    schema: z.object({
      after: lit(z.unknown()).optional(),
      before: lit(z.unknown()).optional(),
      path: lit(z.string()).optional(),
    }),
  },
  ConnectionStatus: {
    name: "ConnectionStatus",
    schema: z.object({
      feed: lit(z.enum(["live", "reconnecting", "offline"])).optional(),
      latencyMs: lit(Bound).optional(),
      run: lit(z.string()).optional(),
    }),
  },
  ErrorNotice: {
    name: "ErrorNotice",
    schema: z.object({
      code: lit(z.string()),
      detail: lit(z.record(z.unknown())).optional(),
      ref: lit(z.string()).optional(),
    }),
  },
  EventRow: {
    name: "EventRow",
    schema: z.object({
      form: lit(z.enum(["original", "projection", "receipt-only"])).optional(),
      seq: lit(Bound).optional(),
      summary: lit(z.string()).optional(),
      type: lit(z.string()).optional(),
    }),
  },
  EvidenceCard: {
    name: "EvidenceCard",
    schema: z.object({
      captured_at: lit(z.string()).optional(),
      kind: lit(z.string()).optional(),
      masks: lit(z.array(z.unknown())).optional(),
      ref: lit(z.string()).optional(),
      task: lit(z.string()).optional(),
      verified_by: lit(z.string()).optional(),
    }),
  },
  GardenerThinking: {
    name: "GardenerThinking",
    schema: z.object({
      actor: lit(z.string()).optional(),
      steps: lit(z.array(z.unknown())).optional(),
    }),
  },
  LiveDocks: {
    name: "LiveDocks",
    schema: z.object({
      docks: lit(z.array(z.unknown())).optional(),
    }),
  },
  LogStream: {
    name: "LogStream",
    schema: z.object({
      entries: lit(z.array(z.unknown())).optional(),
      filter: lit(z.array(z.unknown())).optional(),
    }),
  },
  MediaWithMasks: {
    name: "MediaWithMasks",
    schema: z.object({
      frame: lit(Bound).optional(),
      hidden: lit(z.array(z.unknown())).optional(),
      labels: lit(z.array(z.unknown())).optional(),
      masks: lit(z.array(z.unknown())).optional(),
      media_ref: lit(z.string()).optional(),
    }),
  },
  ProvenanceTag: {
    name: "ProvenanceTag",
    schema: z.object({
      kind: lit(z.enum(["measured", "vault", "signed", "model", "estimate"])).optional(),
      source: lit(z.string()).optional(),
    }),
  },
  ReceiptBadge: {
    name: "ReceiptBadge",
    schema: z.object({
      seq: lit(Bound).optional(),
      state: lit(z.enum(["ok", "bad", "pending"])).optional(),
    }),
  },
  RippleBanner: {
    name: "RippleBanner",
    schema: z.object({
      ripple: lit(z.record(z.unknown())).optional(),
    }),
  },
  StepProgress: {
    name: "StepProgress",
    schema: z.object({
      eta: lit(z.string()).optional(),
      measured: lit(z.array(z.unknown())).optional(),
      planned: lit(z.array(z.unknown())).optional(),
      progress: lit(Bound).optional(),
      task: lit(z.string()).optional(),
    }),
  },
  StewardVerdict: {
    name: "StewardVerdict",
    schema: z.object({
      verdict: lit(z.record(z.unknown())).optional(),
    }),
  },
  VerifyPanel: {
    name: "VerifyPanel",
    schema: z.object({
      checks: lit(z.array(z.unknown())).optional(),
      export: lit(z.record(z.unknown())).optional(),
    }),
  },
};
export const implementations = Object.values(apis).map((api) =>
  createComponentImplementation(api, ({ props, context }) => render(api.name, props, context)),
);
