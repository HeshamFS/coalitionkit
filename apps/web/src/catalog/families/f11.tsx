// SPDX-License-Identifier: Apache-2.0
import { createComponentImplementation } from "@a2ui/react/v0_9";
import { CommonSchemas } from "@a2ui/web_core/v0_9";
import { z } from "zod";
import { render } from "../../components/f11/render";
import { Bound } from "../schemas";

const lit = <T extends z.ZodTypeAny>(schema: T) => z.union([schema, CommonSchemas.DataBinding]);
const subject = z.object({ kind: z.string(), id: z.string(), revision: Bound });
export const apis = {
  ChannelHandoff: {
    name: "ChannelHandoff",
    schema: z.object({
      from: lit(z.string()).optional(),
      reason: lit(z.enum(["money", "identity", "too long"])).optional(),
      subject: lit(subject).optional(),
      to: lit(z.string()).optional(),
    }),
  },
  ChannelSettings: {
    name: "ChannelSettings",
    schema: z.object({
      channels: lit(z.array(z.unknown())).optional(),
      overrides: lit(z.array(z.unknown())).optional(),
      quiet: lit(z.record(z.unknown())).optional(),
    }),
  },
  CoalitionArchive: {
    name: "CoalitionArchive",
    schema: z.object({
      items: lit(z.array(z.unknown())).optional(),
    }),
  },
  CostMeter: {
    name: "CostMeter",
    schema: z.object({
      budget: lit(Bound).optional(),
      rows: lit(z.array(z.unknown())).optional(),
      total: lit(Bound).optional(),
    }),
  },
  DissolveSummary: {
    name: "DissolveSummary",
    schema: z.object({
      contributions: lit(z.array(z.unknown())).optional(),
      cost: lit(z.string()).optional(),
      counts: lit(z.record(z.unknown())).optional(),
      goal: lit(z.string()).optional(),
      log: lit(z.string()).optional(),
      outcome: lit(z.enum(["reached", "partly", "not", "deadline"])).optional(),
    }),
  },
  DoorMatrix: {
    name: "DoorMatrix",
    schema: z.object({
      doors: lit(z.array(z.unknown())).optional(),
      target: lit(z.string()).optional(),
    }),
  },
  ExportControl: {
    name: "ExportControl",
    schema: z.object({
      items: lit(z.array(z.unknown())).optional(),
    }),
  },
  LessonReview: {
    name: "LessonReview",
    schema: z.object({
      lessons: lit(z.array(z.unknown())).optional(),
    }),
  },
  MessageTemplate: {
    name: "MessageTemplate",
    schema: z.object({
      params: lit(z.array(z.unknown())).optional(),
      quickReplies: lit(Bound).optional(),
      template: lit(z.string()).optional(),
    }),
  },
  MetricTile: {
    name: "MetricTile",
    schema: z.object({
      context: lit(z.string()).optional(),
      label: lit(z.string()),
      run: lit(z.string()).optional(),
      unit: lit(z.string()).optional(),
      value: lit(Bound).optional(),
    }),
  },
  NotificationCard: {
    name: "NotificationCard",
    schema: z.object({
      body: lit(z.string()).optional(),
      link: lit(z.string()).optional(),
      title: lit(z.string()),
    }),
  },
  Scorecard: {
    name: "Scorecard",
    schema: z.object({
      tiles: lit(z.array(z.unknown())).optional(),
    }),
  },
  SkillCard: {
    name: "SkillCard",
    schema: z.object({
      name: lit(z.string()),
      roles: lit(z.array(z.unknown())).optional(),
      rules: lit(z.array(z.unknown())).optional(),
      source: lit(z.string()).optional(),
      templates: lit(z.array(z.unknown())).optional(),
    }),
  },
};
export const implementations = Object.values(apis).map((api) =>
  createComponentImplementation(api, ({ props, context }) => render(api.name, props, context)),
);
