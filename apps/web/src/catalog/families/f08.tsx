// SPDX-License-Identifier: Apache-2.0
import { createComponentImplementation } from "@a2ui/react/v0_9";
import { CommonSchemas } from "@a2ui/web_core/v0_9";
import { z } from "zod";
import { render } from "../../components/f08/render";
import { Bound } from "../schemas";

const lit = <T extends z.ZodTypeAny>(schema: T) => z.union([schema, CommonSchemas.DataBinding]);
const subject = z.object({ kind: z.string(), id: z.string(), revision: Bound });
export const apis = {
  ApprovalButton: {
    name: "ApprovalButton",
    schema: z.object({
      consequence: lit(z.string()),
      decision_deadline: lit(z.string()),
      disabledReason: lit(z.string()).optional(),
      label: lit(z.string()),
      subject: lit(subject),
    }),
  },
  CanaryMonitor: {
    name: "CanaryMonitor",
    schema: z.object({
      canaries: lit(Bound).optional(),
      found: lit(Bound).optional(),
      runs: lit(Bound).optional(),
      surfaces: lit(z.array(z.unknown())).optional(),
    }),
  },
  CommitmentCard: {
    name: "CommitmentCard",
    schema: z.object({
      assignee: lit(z.string()).optional(),
      commitment_id: lit(z.string()).optional(),
      decision_deadline: lit(z.string()).optional(),
      due: lit(z.string()).optional(),
      status: lit(
        z.enum(["pending", "approved", "suspended", "withdrawn", "superseded"]),
      ).optional(),
      subject: lit(subject),
      task: lit(z.string()).optional(),
    }),
  },
  ConsentCard: {
    name: "ConsentCard",
    schema: z.object({
      consequence: lit(z.string()),
      consequenceOfNo: lit(z.string()).optional(),
      cost: lit(z.string()).optional(),
      decision_deadline: lit(z.string()),
      subject: lit(subject),
      summary: lit(z.string()).optional(),
      yourPart: lit(z.string()).optional(),
    }),
  },
  DecisionLog: {
    name: "DecisionLog",
    schema: z.object({
      entries: lit(z.array(z.unknown())).optional(),
    }),
  },
  DisclosureLadder: {
    name: "DisclosureLadder",
    schema: z.object({
      buckets: lit(z.array(z.unknown())).optional(),
      field: lit(z.string()).optional(),
      level: lit(z.enum(["none", "bool", "range", "exact"])).optional(),
      overrides: lit(z.array(z.unknown())).optional(),
    }),
  },
  DurableConsent: {
    name: "DurableConsent",
    schema: z.object({
      grants: lit(z.array(z.unknown())).optional(),
      requests: lit(z.array(z.unknown())).optional(),
    }),
  },
  OverlapView: {
    name: "OverlapView",
    schema: z.object({
      mode: lit(z.enum(["intersection", "count-only"])).optional(),
      parties: lit(z.array(z.unknown())).optional(),
      result: lit(z.enum(["slots", "count"])).optional(),
      run: lit(z.string()).optional(),
      tokens: lit(z.array(z.unknown())).optional(),
    }),
  },
  PrivateField: {
    name: "PrivateField",
    schema: z.object({
      display: lit(z.string()),
      policy: lit(z.string()).optional(),
      reveal: lit(Bound).optional(),
    }),
  },
  ProjectionNote: {
    name: "ProjectionNote",
    schema: z.object({
      removed: lit(Bound).optional(),
      source: lit(z.record(z.unknown())).optional(),
      viewerSpecific: lit(z.boolean()).optional(),
    }),
  },
  RedactionDiff: {
    name: "RedactionDiff",
    schema: z.object({
      delivered: lit(z.string()).optional(),
      original: lit(z.string()).optional(),
      verdict: lit(z.record(z.unknown())).optional(),
    }),
  },
  ScopeBadge: {
    name: "ScopeBadge",
    schema: z.object({
      audience: lit(z.string()).optional(),
      redact: lit(z.array(z.unknown())).optional(),
    }),
  },
  StaleNotice: {
    name: "StaleNotice",
    schema: z.object({
      currentRevision: lit(Bound).optional(),
      decision_deadline: lit(z.string()).optional(),
      diff: lit(z.array(z.unknown())).optional(),
      subject: lit(subject),
      yourRevision: lit(Bound).optional(),
    }),
  },
  VaultCard: {
    name: "VaultCard",
    schema: z.object({
      answersToday: lit(Bound).optional(),
      categories: lit(z.array(z.unknown())).optional(),
      location: lit(z.enum(["device", "self-hosted"])).optional(),
    }),
  },
  VoteTally: {
    name: "VoteTally",
    schema: z.object({
      answered: lit(Bound).optional(),
      answers: lit(z.array(z.unknown())).optional(),
      deciders: lit(z.array(z.unknown())).optional(),
      decision_deadline: lit(z.string()).optional(),
      outcome: lit(z.enum(["decided", "refused", "split", "expired"])).optional(),
      rule: lit(z.string()).optional(),
      subject: lit(subject),
    }),
  },
  WhatOthersKnow: {
    name: "WhatOthersKnow",
    schema: z.object({
      rows: lit(z.array(z.unknown())).optional(),
    }),
  },
};
export const implementations = Object.values(apis).map((api) =>
  createComponentImplementation(api, ({ props, context }) => render(api.name, props, context)),
);
