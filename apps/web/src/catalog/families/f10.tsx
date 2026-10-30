// SPDX-License-Identifier: Apache-2.0
import { createComponentImplementation } from "@a2ui/react/v0_9";
import { CommonSchemas } from "@a2ui/web_core/v0_9";
import { z } from "zod";
import { render } from "../../components/f10/render";
import { Bound } from "../schemas";

const lit = <T extends z.ZodTypeAny>(schema: T) => z.union([schema, CommonSchemas.DataBinding]);
export const apis = {
  AttackTests: {
    name: "AttackTests",
    schema: z.object({
      tests: lit(z.array(z.unknown())).optional(),
    }),
  },
  CaptureCard: {
    name: "CaptureCard",
    schema: z.object({
      masks: lit(z.array(z.unknown())).optional(),
      narration: lit(z.string()).optional(),
      tips: lit(z.array(z.unknown())).optional(),
      video: lit(z.string()).optional(),
    }),
  },
  DeviceAlarm: {
    name: "DeviceAlarm",
    schema: z.object({
      autoAction: lit(z.string()).optional(),
      device: lit(z.string()).optional(),
      duration: lit(Bound).optional(),
      reading: lit(Bound).optional(),
      threshold: lit(Bound).optional(),
    }),
  },
  DeviceReading: {
    name: "DeviceReading",
    schema: z.object({
      annotations: lit(z.array(z.unknown())).optional(),
      limits: lit(z.array(z.unknown())).optional(),
      planned: lit(z.array(z.unknown())).optional(),
      series: lit(z.array(z.unknown())).optional(),
      source: lit(z.string()).optional(),
      unit: lit(z.string()).optional(),
    }),
  },
  EdgeReaderStatus: {
    name: "EdgeReaderStatus",
    schema: z.object({
      confidence: lit(Bound).optional(),
      fallback: lit(z.string()).optional(),
      framesKept: lit(z.string()).optional(),
      rate: lit(Bound).optional(),
      source: lit(z.enum(["camera", "serial", "vendor app"])).optional(),
    }),
  },
  MintPipeline: {
    name: "MintPipeline",
    schema: z.object({
      cost: lit(z.string()).optional(),
      elapsed: lit(Bound).optional(),
      stages: lit(z.array(z.unknown())).optional(),
    }),
  },
  MintedAgentCard: {
    name: "MintedAgentCard",
    schema: z.object({
      agent: lit(z.record(z.unknown())).optional(),
      health: lit(z.string()).optional(),
      readings: lit(z.array(z.unknown())).optional(),
      tools: lit(z.array(z.unknown())).optional(),
    }),
  },
  PublishApproval: {
    name: "PublishApproval",
    schema: z.object({
      coalitions: lit(z.array(z.unknown())).optional(),
      spec: lit(z.record(z.unknown())).optional(),
      tests: lit(z.record(z.unknown())).optional(),
    }),
  },
  ScheduleTwin: {
    name: "ScheduleTwin",
    schema: z.object({
      machines: lit(z.array(z.unknown())).optional(),
    }),
  },
};
export const implementations = Object.values(apis).map((api) =>
  createComponentImplementation(api, ({ props, context }) => render(api.name, props, context)),
);
