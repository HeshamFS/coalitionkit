// SPDX-License-Identifier: Apache-2.0
import { createComponentImplementation, type ReactComponentImplementation } from "@a2ui/react/v0_9";
import { CommonSchemas } from "@a2ui/web_core/v0_9";
import { z } from "zod";
import { WireValue } from "../../components/f05/wire";
import * as Views from "../../components/f06/views";
import { emit } from "../implementations";
import { Bound } from "../schemas";

const binding = CommonSchemas.DataBinding;
const literal = <T extends z.ZodTypeAny>(schema: T) => z.union([schema, binding]);
export const apis = {
  AnswerCard: {
    name: "AnswerCard",
    schema: z.object({
      answer: literal(WireValue).optional(),
      from: literal(z.string()).optional(),
      kind: literal(z.enum(["bool", "number-range", "choice"])).optional(),
      query: literal(z.string()).optional(),
      task_id: literal(z.string()).optional(),
    }),
  },
  AssignmentRow: {
    name: "AssignmentRow",
    schema: z.object({
      assignments: literal(z.array(WireValue).max(200)).optional(),
      fit: literal(z.string()).optional(),
      hours: literal(Bound).optional(),
      share: literal(Bound).optional(),
    }),
  },
  Checklist: {
    name: "Checklist",
    schema: z.object({
      items: literal(z.array(WireValue).max(200)).optional(),
    }),
  },
  CostSplit: {
    name: "CostSplit",
    schema: z.object({
      items: literal(z.array(WireValue).max(200)).optional(),
      rule: literal(z.enum(["even", "by share", "by use"])).optional(),
      settlements: literal(z.array(WireValue).max(200)).optional(),
    }),
  },
  DependencyGraph: {
    name: "DependencyGraph",
    schema: z.object({
      changed: literal(z.string()).optional(),
      edges: literal(z.array(WireValue).max(200)).optional(),
      invalidated: literal(z.array(WireValue).max(200)).optional(),
      nodes: literal(z.array(WireValue).max(200)).optional(),
    }),
  },
  FairnessMeter: {
    name: "FairnessMeter",
    schema: z.object({
      cap: literal(Bound).optional(),
      rows: literal(z.array(WireValue).max(200)).optional(),
    }),
  },
  Gantt: {
    name: "Gantt",
    schema: z.object({
      criticalPath: literal(z.array(WireValue).max(200)).optional(),
      deadlines: literal(z.array(WireValue).max(200)).optional(),
      now: literal(z.string()).optional(),
      rows: literal(z.array(WireValue).max(200)).optional(),
      zoom: literal(z.enum(["hours", "days", "weeks"])).optional(),
    }),
  },
  MatchView: {
    name: "MatchView",
    schema: z.object({
      chosen: literal(z.string()).optional(),
      need: literal(z.string()).optional(),
      offers: literal(z.array(WireValue).max(200)).optional(),
    }),
  },
  NeedCard: {
    name: "NeedCard",
    schema: z.object({
      by: literal(z.string()).optional(),
      constraints: literal(z.array(WireValue).max(200)).optional(),
      need_id: literal(z.string()).optional(),
      offers: literal(Bound).optional(),
      owner: literal(z.string()).optional(),
      state: literal(z.enum(["open", "matched", "fulfilled", "withdrawn"])).optional(),
      text: literal(z.string()),
    }),
  },
  ObjectiveBars: {
    name: "ObjectiveBars",
    schema: z.object({
      objectives: literal(z.array(WireValue).max(200)).optional(),
    }),
  },
  OfferCard: {
    name: "OfferCard",
    schema: z.object({
      conditions: literal(z.array(WireValue).max(200)).optional(),
      cost: literal(z.record(WireValue)).optional(),
      expires: literal(z.string()).optional(),
      offer_id: literal(z.string()).optional(),
      scope: literal(z.union([z.string(), z.record(WireValue)])).optional(),
      state: literal(z.enum(["open", "accepted", "expired", "withdrawn"])).optional(),
      target: literal(z.enum(["need", "task"])).optional(),
      what: literal(z.string()).optional(),
    }),
  },
  PlanCompare: {
    name: "PlanCompare",
    schema: z.object({
      decision_deadline: literal(z.string()).optional(),
      plans: literal(z.array(WireValue).max(8)),
      proposal_set_id: literal(z.string()).optional(),
      rejected: literal(z.array(WireValue).max(8)).optional(),
    }),
  },
  TaskCard: {
    name: "TaskCard",
    schema: z.object({
      assignee: literal(z.string()).optional(),
      deps: literal(z.record(WireValue)).optional(),
      evidence: literal(z.string()).optional(),
      status: literal(
        z.enum(["open", "negotiating", "proposed", "decided", "committed", "done", "withdrawn"]),
      ).optional(),
      task_id: literal(z.string()).optional(),
      title: literal(z.string()),
      window: literal(z.record(WireValue)).optional(),
    }),
  },
  TensionCard: {
    name: "TensionCard",
    schema: z.object({
      answered: literal(Bound).optional(),
      deciders: literal(z.array(WireValue).max(50)),
      decision_deadline: literal(z.string()),
      options: literal(z.array(WireValue).max(12)),
      subject: literal(z.object({ kind: z.string(), id: z.string(), revision: Bound })),
      task_ids: literal(z.array(WireValue).max(200)).optional(),
      tension_id: literal(z.string()).optional(),
    }),
  },
  Timeline: {
    name: "Timeline",
    schema: z.object({
      items: literal(z.array(WireValue).max(200)).optional(),
      now: literal(z.string()).optional(),
    }),
  },
};
export const implementations: ReactComponentImplementation[] = [
  createComponentImplementation(apis.AnswerCard, ({ props, context }) => (
    <Views.AnswerCard p={props} send={(name, data) => emit(context, name, data)} />
  )),
  createComponentImplementation(apis.AssignmentRow, ({ props, context }) => (
    <Views.AssignmentRow p={props} send={(name, data) => emit(context, name, data)} />
  )),
  createComponentImplementation(apis.Checklist, ({ props, context }) => (
    <Views.Checklist p={props} send={(name, data) => emit(context, name, data)} />
  )),
  createComponentImplementation(apis.CostSplit, ({ props, context }) => (
    <Views.CostSplit p={props} send={(name, data) => emit(context, name, data)} />
  )),
  createComponentImplementation(apis.DependencyGraph, ({ props, context }) => (
    <Views.DependencyGraph p={props} send={(name, data) => emit(context, name, data)} />
  )),
  createComponentImplementation(apis.FairnessMeter, ({ props, context }) => (
    <Views.FairnessMeter p={props} send={(name, data) => emit(context, name, data)} />
  )),
  createComponentImplementation(apis.Gantt, ({ props, context }) => (
    <Views.Gantt p={props} send={(name, data) => emit(context, name, data)} />
  )),
  createComponentImplementation(apis.MatchView, ({ props, context }) => (
    <Views.MatchView p={props} send={(name, data) => emit(context, name, data)} />
  )),
  createComponentImplementation(apis.NeedCard, ({ props, context }) => (
    <Views.NeedCard p={props} send={(name, data) => emit(context, name, data)} />
  )),
  createComponentImplementation(apis.ObjectiveBars, ({ props, context }) => (
    <Views.ObjectiveBars p={props} send={(name, data) => emit(context, name, data)} />
  )),
  createComponentImplementation(apis.OfferCard, ({ props, context }) => (
    <Views.OfferCard p={props} send={(name, data) => emit(context, name, data)} />
  )),
  createComponentImplementation(apis.PlanCompare, ({ props, context }) => (
    <Views.PlanCompare p={props} send={(name, data) => emit(context, name, data)} />
  )),
  createComponentImplementation(apis.TaskCard, ({ props, context }) => (
    <Views.TaskCard p={props} send={(name, data) => emit(context, name, data)} />
  )),
  createComponentImplementation(apis.TensionCard, ({ props, context }) => (
    <Views.TensionCard p={props} send={(name, data) => emit(context, name, data)} />
  )),
  createComponentImplementation(apis.Timeline, ({ props, context }) => (
    <Views.Timeline p={props} send={(name, data) => emit(context, name, data)} />
  )),
];
